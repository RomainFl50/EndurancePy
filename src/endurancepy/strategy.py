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

__all__ = ["driver_summary", "lead_changes", "pit_stops", "stint_summary"]

#: Columns (and dtypes) of the pit-stop table returned by :func:`pit_stops`.
_PIT_STOP_DTYPES: dict[str, str] = {
    "CarNumber": "string",
    "Lap": "Int64",
    "Stint": "Int64",
    "PitTime": "timedelta64[ns]",
    "Class": "string",
    "Manufacturer": "string",
    "TeamName": "string",
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


def pit_stops(source: Laps | Session | pd.DataFrame) -> pd.DataFrame:
    """One row per pit stop, derived from the laps.

    A stop is an in-lap (a lap crossing the line in the pits). Each row gives the
    car, the in-lap number, the stint that just ended, the reported time in the
    pits (``PitTime``, may be ``NaT`` when the source omits it) and the car's
    class / manufacturer / team. Ordered by lap then car.
    """
    frame = _laps_frame(source)
    if frame.empty or "PitInTime" not in frame:
        return pd.DataFrame({name: [] for name in _PIT_STOP_DTYPES}).astype(
            _PIT_STOP_DTYPES
        )

    stops = frame[frame["PitInTime"].notna()]
    table = pd.DataFrame(
        {
            "CarNumber": stops["CarNumber"],
            "Lap": stops["LapNumber"],
            "Stint": stops["Stint"],
            "PitTime": stops["PitTime"],
            "Class": stops["Class"],
            "Manufacturer": stops["Manufacturer"],
            "TeamName": stops["Team"],
        }
    )
    table = table.astype(_PIT_STOP_DTYPES)
    return table.sort_values(["Lap", "CarNumber"]).reset_index(drop=True)


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
