"""Season-level driver pace, optionally grouped by FIA driver category.

This is the business logic behind a "best driver per grade" ranking: it takes
the race laps of several rounds and ranks drivers by how close their pace was to
the fastest driver of their class, averaged across the races they ran.

Method (per race, per ``(Class, CarNumber, Driver)``):

* keep only clean laps — timed, no pit in/out, not the opening lap, and (when
  the ``IsAccurate`` flag is present) accurate laps only, which drops laps run
  under a non-green track status;
* require at least ``min_laps`` such laps;
* take the mean of the fastest ``top_fraction`` of them (a robust "representative
  pace", min. 5 laps);
* express it as a percentage gap to the fastest representative pace of the same
  class in that race.

Across races, a driver's figure is the mean of their per-race gaps.

FIA categories (Platinum / Gold / Silver / Bronze) are **not** carried by the Al
Kamel timing CSVs, so they are supplied by the caller via ``categories`` (a
mapping of driver name to category). The match tolerates case, accents and word
order. When no category is known the driver is still ranked; its ``Category`` is
left blank, so a caller can fall back to a per-class view.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

__all__ = ["driver_pace", "CATEGORY_LABELS"]

#: FIA category codes to human labels (French, matching the dashboard).
CATEGORY_LABELS = {"P": "Platinum", "G": "Gold", "S": "Silver", "B": "Bronze"}

_PACE_DTYPES = {
    "Driver": "string",
    "Category": "string",
    "Class": "string",
    "MeanGapPercent": "float64",
    "Races": "int64",
    "Laps": "int64",
}


def _ascii_lower(name: Any) -> str:
    return (
        unicodedata.normalize("NFKD", str(name or ""))
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )


def _norm_name(name: Any) -> str:
    """Letters only, lowercased and unaccented (``"Sébastien BOURDAIS"`` -> ...)."""
    return "".join(ch for ch in _ascii_lower(name) if ch.isalpha())


def _name_key(name: Any) -> str:
    """Word-order-independent key: sorted lowercased letter tokens.

    Griiip entry lists and Al Kamel CSVs sometimes order a name differently
    (``"Will Stevens"`` vs ``"Stevens Will"``); this makes a category lookup
    survive that.
    """
    tokens = [
        tok for tok in _ascii_lower(name).replace("-", " ").split() if tok.isalpha()
    ]
    return " ".join(sorted(tokens))


def _build_category_index(categories: Mapping[str, str] | None) -> dict[str, str]:
    index: dict[str, str] = {}
    for name, cat in (categories or {}).items():
        code = str(cat or "").upper()[:1]
        if code in CATEGORY_LABELS:
            index[_norm_name(name)] = code
            index[_name_key(name)] = code
    return index


def _lookup_category(index: dict[str, str], driver: Any) -> str:
    return index.get(_norm_name(driver)) or index.get(_name_key(driver)) or ""


def _laps_frame(source: Any) -> pd.DataFrame:
    """Accept a Session (use its ``laps``), a Laps or a plain DataFrame."""
    laps = getattr(source, "laps", source)
    if isinstance(laps, pd.DataFrame):
        return laps
    return pd.DataFrame(laps)


def _clean_pace_laps(group: pd.DataFrame, *, accurate_only: bool) -> pd.DataFrame:
    """Timed laps representative of pure pace (no pit in/out, no opening lap)."""
    mask = group["LapTime"].notna()
    if "LapNumber" in group:
        mask &= group["LapNumber"] != 1
    if "PitInTime" in group:
        mask &= group["PitInTime"].isna()
    if "PitOutTime" in group:
        mask &= group["PitOutTime"].isna()
    if accurate_only and "IsAccurate" in group:
        mask &= group["IsAccurate"].fillna(False).astype(bool)
    return group[mask]


def _empty_pace() -> pd.DataFrame:
    return pd.DataFrame(
        {name: pd.Series(dtype=dt) for name, dt in _PACE_DTYPES.items()}
    )


def driver_pace(
    races: Iterable[Any],
    *,
    categories: Mapping[str, str] | None = None,
    min_laps: int = 10,
    top_fraction: float = 0.2,
    accurate_only: bool = True,
) -> pd.DataFrame:
    """Rank drivers by representative race pace, across several rounds.

    Parameters
    ----------
    races:
        One lap source per round — a :class:`~endurancepy.core.Session`, a
        :class:`~endurancepy.core.Laps`, or a plain ``DataFrame`` with at least
        ``CarNumber``, ``Driver``, ``Class`` and ``LapTime`` columns.
    categories:
        Optional mapping of driver name to FIA category (``"P"``/``"G"``/``"S"``
        /``"B"``, or the full label). Used only to fill the ``Category`` column;
        matching is case/accent/word-order tolerant.
    min_laps:
        Minimum clean laps a driver must have in a race to count there.
    top_fraction:
        Fraction of fastest clean laps averaged into the representative pace
        (at least 5 laps).
    accurate_only:
        When ``True`` and an ``IsAccurate`` column is present, keep only accurate
        laps (drops laps under a non-green track status).

    Returns
    -------
    DataFrame
        One row per ``(Class, Driver)``: ``Driver``, ``Category``, ``Class``,
        ``MeanGapPercent`` (mean % gap to the class's best pace across the
        driver's races), ``Races`` and ``Laps``. Sorted by ``MeanGapPercent``.
    """
    cat_index = _build_category_index(categories)
    per_race: list[dict[tuple[str, str], dict[str, Any]]] = []

    for source in races:
        frame = _laps_frame(source)
        if frame.empty or "Driver" not in frame or "LapTime" not in frame:
            continue
        gaps: dict[tuple[str, str, str], dict[str, Any]] = {}
        for (cls, car, driver), group in frame.dropna(subset=["Driver"]).groupby(
            ["Class", "CarNumber", "Driver"], sort=False
        ):
            clean = _clean_pace_laps(group, accurate_only=accurate_only)
            secs = clean["LapTime"].dt.total_seconds().dropna().sort_values()
            if len(secs) < min_laps:
                continue
            count = max(5, int(len(secs) * top_fraction))
            pace = float(secs.iloc[:count].mean())
            gaps[(str(cls), str(car), str(driver))] = {
                "pace": pace,
                "laps": int(len(secs)),
            }
        # Best representative pace per class in this race.
        best: dict[str, float] = {}
        for (cls, _car, _driver), rec in gaps.items():
            best[cls] = min(best.get(cls, float("inf")), rec["pace"])
        race_rows: dict[tuple[str, str], dict[str, Any]] = {}
        for (cls, _car, driver), rec in gaps.items():
            race_rows[(cls, driver)] = {
                "gap": 100.0 * (rec["pace"] / best[cls] - 1.0),
                "laps": rec["laps"],
            }
        per_race.append(race_rows)

    # Aggregate across races by (Class, Driver).
    agg: dict[tuple[str, str], dict[str, Any]] = {}
    for race_rows in per_race:
        for (cls, driver), rec in race_rows.items():
            record = agg.setdefault(
                (cls, driver), {"gaps": [], "laps": 0, "driver": driver, "cls": cls}
            )
            record["gaps"].append(rec["gap"])
            record["laps"] += rec["laps"]

    if not agg:
        return _empty_pace()

    rows = []
    for (cls, driver), record in agg.items():
        gaps_list = record["gaps"]
        rows.append(
            {
                "Driver": driver,
                "Category": _lookup_category(cat_index, driver),
                "Class": cls,
                "MeanGapPercent": sum(gaps_list) / len(gaps_list),
                "Races": len(gaps_list),
                "Laps": record["laps"],
            }
        )
    table = pd.DataFrame(rows).astype(_PACE_DTYPES)
    return table.sort_values(["MeanGapPercent", "Driver"]).reset_index(drop=True)
