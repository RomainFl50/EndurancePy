"""Race-craft / strategy analysis derived from the laps (milestone 0.4.0).

Endurance racing is won and lost on strategy, so this module turns the lap table
into the artefacts an analyst reaches for first. It starts with pit stops; stint
degradation, on-track gaps and battle detection follow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from endurancepy.core import Laps, Session

__all__ = [
    "battles",
    "driver_summary",
    "fuel_corrected",
    "lead_changes",
    "pit_stops",
    "stint_summary",
]

#: Columns (and dtypes) of the pit-stop table returned by :func:`pit_stops`.
_PIT_STOP_DTYPES: dict[str, str] = {
    "CarNumber": "string",
    "Lap": "Int64",
    "Stint": "Int64",
    "PitTime": "timedelta64[ns]",
    "Class": "string",
    "Manufacturer": "string",
    "TeamName": "string",
    "PosBefore": "Int64",  # overall position on the lap before the stop
    "PosAfter": "Int64",  # overall position `settle` laps after the stop
    "PlacesGained": "Int64",  # PosBefore - PosAfter (+ = undercut/overcut worked)
}

#: Columns (and dtypes) of the stint table returned by :func:`stint_summary`.
_STINT_DTYPES: dict[str, str] = {
    "CarNumber": "string",
    "Stint": "Int64",
    "Class": "string",
    "Driver": "string",
    "Laps": "Int64",
    "StartLap": "Int64",
    "EndLap": "Int64",
    "BestLap": "timedelta64[ns]",
    "MedianLap": "timedelta64[ns]",
    "Degradation": "float64",  # lap-time trend, seconds per lap (+ = slowing)
}

#: Columns (and dtypes) of the driver table returned by :func:`driver_summary`.
_DRIVER_DTYPES: dict[str, str] = {
    "CarNumber": "string",
    "Driver": "string",
    "Class": "string",
    "Laps": "Int64",
    "TimeInCar": "timedelta64[ns]",
    "BestLap": "timedelta64[ns]",
    "MedianLap": "timedelta64[ns]",
    "Consistency": "float64",  # std-dev of clean lap times, in seconds
}


#: Columns (and dtypes) of the lead table returned by :func:`lead_changes`.
_LEAD_DTYPES: dict[str, str] = {
    "Class": "string",
    "Leader": "string",
    "FromLap": "Int64",
    "ToLap": "Int64",
    "Laps": "Int64",
}

#: Columns (and dtypes) of the battle table returned by :func:`battles`.
_BATTLE_DTYPES: dict[str, str] = {
    "Class": "string",
    "CarA": "string",
    "CarB": "string",
    "FromLap": "Int64",
    "ToLap": "Int64",
    "Laps": "Int64",
    "MinGap": "timedelta64[ns]",
    "MeanGap": "timedelta64[ns]",
}


def _car_key(car: str) -> tuple[int, Any]:
    text = str(car)
    return (0, int(text)) if text.isdigit() else (1, text)


def _empty(dtypes: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame({name: [] for name in dtypes}).astype(dtypes)


def _drivers(values: pd.Series) -> str:
    return "; ".join(dict.fromkeys(values.dropna().astype(str)))


def _clean_laps(group: pd.DataFrame) -> pd.DataFrame:
    """Timed laps with no pit in/out — representative of pure pace."""
    mask = group["LapTime"].notna()
    if "PitInTime" in group:
        mask &= group["PitInTime"].isna()
    if "PitOutTime" in group:
        mask &= group["PitOutTime"].isna()
    return group[mask]


def _laps_frame(source: Any) -> pd.DataFrame:
    """Accept a Session (use its ``laps``) or a Laps/DataFrame directly."""
    laps = getattr(source, "laps", source)
    return pd.DataFrame(laps)


def pit_stops(
    source: Laps | Session | pd.DataFrame, *, settle: int = 2
) -> pd.DataFrame:
    """One row per pit stop, derived from the laps.

    A stop is an in-lap (a lap crossing the line in the pits). Each row gives the
    car, the in-lap number, the stint that just ended, the reported time in the
    pits (``PitTime``, may be ``NaT``), the car's class / manufacturer / team, and
    the overall position before the stop (`PosBefore`, the previous lap) versus
    ``settle`` laps after it (`PosAfter`). `PlacesGained = PosBefore - PosAfter` is
    a rough undercut/overcut outcome (positive = places gained across the stop).
    Ordered by lap then car.
    """
    frame = _laps_frame(source)
    if frame.empty or "PitInTime" not in frame:
        return _empty(_PIT_STOP_DTYPES)
    stops = frame[frame["PitInTime"].notna()]
    if stops.empty:
        return _empty(_PIT_STOP_DTYPES)

    positions: dict[tuple[str, float], int] = {}
    if "Position" in frame:
        located = frame.dropna(subset=["LapNumber", "Position"])
        positions = {
            (str(car), float(lap)): int(pos)
            for car, lap, pos in zip(
                located["CarNumber"],
                located["LapNumber"],
                located["Position"],
                strict=True,
            )
        }

    rows = []
    for stop in stops.itertuples(index=False):
        car = str(stop.CarNumber)
        lap = float(stop.LapNumber)
        before = positions.get((car, lap - 1))
        after = positions.get((car, lap + settle))
        rows.append(
            {
                "CarNumber": stop.CarNumber,
                "Lap": stop.LapNumber,
                "Stint": stop.Stint,
                "PitTime": stop.PitTime,
                "Class": stop.Class,
                "Manufacturer": stop.Manufacturer,
                "TeamName": stop.Team,
                "PosBefore": before,
                "PosAfter": after,
                "PlacesGained": (
                    before - after if before is not None and after is not None else None
                ),
            }
        )
    table = pd.DataFrame(rows).astype(_PIT_STOP_DTYPES)
    return table.sort_values(["Lap", "CarNumber"]).reset_index(drop=True)


def fuel_corrected(source: Laps | Session | pd.DataFrame, *, rate: float) -> pd.Series:
    """Fuel-correct each lap to its stint-start (full-tank) fuel load.

    Cars get lighter and faster through a stint; ``rate`` is how many **seconds
    per lap** of fuel that benefit is worth. The correction adds ``rate`` × (laps
    of fuel already burned) back onto each lap, so the returned lap times are
    comparable at a common fuel load — what's left is tyre degradation, traffic
    and driver pace. Returns a ``Timedelta`` Series aligned to the laps.
    """
    frame = _laps_frame(source)
    if frame.empty or "LapTime" not in frame:
        return pd.Series([], dtype="timedelta64[ns]")
    by = ["CarNumber", "Stint"] if "Stint" in frame else ["CarNumber"]
    stint_start = frame.groupby(by)["LapNumber"].transform("min")
    burned = frame["LapNumber"] - stint_start  # laps of fuel used (0 at stint start)
    correction = pd.to_timedelta(rate * burned, unit="s")
    return frame["LapTime"] + correction


def stint_summary(source: Laps | Session | pd.DataFrame) -> pd.DataFrame:
    """One row per ``(car, stint)``: pace and tyre/fuel degradation.

    For each stint: its driver(s), lap span, best and median lap (over clean laps
    — timed, no pit in/out), and **`Degradation`**, the slope of lap time vs
    lap-in-stint in seconds/lap (positive = slowing; ``NaN`` with fewer than two
    clean laps). Ordered by car then stint.
    """
    frame = _laps_frame(source)
    if frame.empty or "Stint" not in frame:
        return _empty(_STINT_DTYPES)

    rows = []
    for (car, stint), group in frame.dropna(subset=["Stint"]).groupby(
        ["CarNumber", "Stint"], sort=True
    ):
        clean = _clean_laps(group)
        pace = clean if not clean.empty else group[group["LapTime"].notna()]
        rows.append(
            {
                "CarNumber": car,
                "Stint": stint,
                "Class": group["Class"].iloc[-1],
                "Driver": _drivers(group["Driver"]),
                "Laps": len(group),
                "StartLap": group["LapNumber"].min(),
                "EndLap": group["LapNumber"].max(),
                "BestLap": pace["LapTime"].min(),
                "MedianLap": pace["LapTime"].median(),
                "Degradation": _degradation(group, clean),
            }
        )
    table = pd.DataFrame(rows).astype(_STINT_DTYPES)
    return table.sort_values(["CarNumber", "Stint"]).reset_index(drop=True)


def _degradation(stint: pd.DataFrame, clean: pd.DataFrame) -> float:
    """Slope (s/lap) of clean lap time vs lap-in-stint; ``NaN`` if under 2 laps."""
    if len(clean) < 2:
        return float("nan")
    start = stint["LapNumber"].min()
    x = (clean["LapNumber"] - start + 1).to_numpy(dtype=float)
    y = clean["LapTime"].dt.total_seconds().to_numpy(dtype=float)
    return float(np.polyfit(x, y, 1)[0])


def driver_summary(source: Laps | Session | pd.DataFrame) -> pd.DataFrame:
    """One row per ``(car, driver)``: laps, time in car, pace and consistency.

    Pace stats (`BestLap`, `MedianLap`, `Consistency` = std-dev in seconds) are
    over clean laps (timed, no pit in/out); `TimeInCar` sums every timed lap the
    driver did. Ordered by car then driver.
    """
    frame = _laps_frame(source)
    if frame.empty or "Driver" not in frame:
        return _empty(_DRIVER_DTYPES)

    rows = []
    for (car, driver), group in frame.dropna(subset=["Driver"]).groupby(
        ["CarNumber", "Driver"], sort=True
    ):
        timed = group[group["LapTime"].notna()]
        clean = _clean_laps(group)
        pace = clean if not clean.empty else timed
        seconds = pace["LapTime"].dt.total_seconds()
        rows.append(
            {
                "CarNumber": car,
                "Driver": driver,
                "Class": group["Class"].iloc[-1],
                "Laps": len(group),
                "TimeInCar": timed["LapTime"].sum() if not timed.empty else pd.NaT,
                "BestLap": pace["LapTime"].min(),
                "MedianLap": pace["LapTime"].median(),
                "Consistency": float(seconds.std()) if len(pace) >= 2 else float("nan"),
            }
        )
    table = pd.DataFrame(rows).astype(_DRIVER_DTYPES)
    return table.sort_values(["CarNumber", "Driver"]).reset_index(drop=True)


def lead_changes(
    source: Laps | Session | pd.DataFrame, *, in_class: bool = False
) -> pd.DataFrame:
    """Leadership periods over the race — one row per stint in the lead.

    Each row is a contiguous run of laps led by one car (``Leader``, ``FromLap``,
    ``ToLap``, ``Laps``); the transitions between rows are the lead changes. With
    ``in_class=True`` the lead is computed per class (``Class`` is set), otherwise
    overall (``Class`` is ``<NA>``). Ordered by first lap.
    """
    frame = _laps_frame(source)
    column = "PositionInClass" if in_class else "Position"
    if frame.empty or column not in frame or "LapNumber" not in frame:
        return _empty(_LEAD_DTYPES)

    leaders = frame[frame[column] == 1].dropna(subset=["LapNumber"])
    if leaders.empty:
        return _empty(_LEAD_DTYPES)

    groups = leaders.groupby("Class") if in_class else [(pd.NA, leaders)]
    rows = []
    for klass, group in groups:
        group = group.sort_values("LapNumber")
        cars = group["CarNumber"].tolist()
        laps = group["LapNumber"].tolist()
        start = 0
        for i in range(1, len(cars) + 1):
            if i == len(cars) or cars[i] != cars[start]:
                rows.append(
                    {
                        "Class": klass,
                        "Leader": cars[start],
                        "FromLap": laps[start],
                        "ToLap": laps[i - 1],
                        "Laps": i - start,
                    }
                )
                start = i
    table = pd.DataFrame(rows).astype(_LEAD_DTYPES)
    return table.sort_values(["FromLap", "Class"]).reset_index(drop=True)


def battles(
    source: Laps | Session | pd.DataFrame,
    *,
    within: str = "1s",
    min_laps: int = 3,
    in_class: bool = True,
) -> pd.DataFrame:
    """Find on-track battles — pairs of cars running nose-to-tail.

    Two cars are "battling" while they are **adjacent in the order** (consecutive
    on elapsed time at equal lap count) and within ``within`` of each other for at
    least ``min_laps`` consecutive laps — regardless of who is ahead, so a
    position swap doesn't end the fight. With ``in_class=True`` the order is taken
    within each class. Returns one row per battle (the pair, lap span, and the
    closest / mean gap), ordered by first lap.
    """
    frame = _laps_frame(source)
    if frame.empty or not {"LapNumber", "Time", "CarNumber"} <= set(frame.columns):
        return _empty(_BATTLE_DTYPES)
    threshold = pd.Timedelta(within)
    work = frame.dropna(subset=["LapNumber", "Time"])
    keys = ["LapNumber", "Class"] if in_class else ["LapNumber"]
    if in_class and "Class" not in work:
        return _empty(_BATTLE_DTYPES)

    # Per lap (and class), record adjacent pairs whose gap is within the threshold.
    seen: dict[tuple[Any, str, str], list[tuple[float, pd.Timedelta]]] = {}
    for key, group in work.groupby(keys, sort=True):
        lap = key[0] if isinstance(key, tuple) else key
        klass = key[1] if (in_class and isinstance(key, tuple)) else pd.NA
        ordered = group.sort_values("Time")
        cars = ordered["CarNumber"].tolist()
        times = ordered["Time"].tolist()
        for i in range(len(cars) - 1):
            gap = times[i + 1] - times[i]
            if gap <= threshold:
                pair = tuple(sorted([cars[i], cars[i + 1]], key=_car_key))
                seen.setdefault((klass, pair[0], pair[1]), []).append((float(lap), gap))

    rows = []
    for (klass, car_a, car_b), entries in seen.items():
        entries.sort(key=lambda item: item[0])
        laps = [lap for lap, _ in entries]
        gaps = [gap for _, gap in entries]
        start = 0
        for i in range(1, len(laps) + 1):
            if i == len(laps) or laps[i] != laps[i - 1] + 1:
                run = slice(start, i)
                if i - start >= min_laps:
                    run_gaps = gaps[run]
                    rows.append(
                        {
                            "Class": klass,
                            "CarA": car_a,
                            "CarB": car_b,
                            "FromLap": laps[start],
                            "ToLap": laps[i - 1],
                            "Laps": i - start,
                            "MinGap": min(run_gaps),
                            "MeanGap": sum(run_gaps, pd.Timedelta(0)) / len(run_gaps),
                        }
                    )
                start = i
    if not rows:
        return _empty(_BATTLE_DTYPES)
    table = pd.DataFrame(rows).astype(_BATTLE_DTYPES)
    return table.sort_values(["FromLap", "Class", "CarA"]).reset_index(drop=True)
