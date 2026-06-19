"""Race-craft / strategy analysis derived from the laps (milestone 0.4.0).

Endurance racing is won and lost on strategy, so this module turns the lap table
into the artefacts an analyst reaches for first. It starts with pit stops; stint
degradation, on-track gaps and battle detection follow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from endurancepy.core import Laps, Session

__all__ = ["pit_stops"]

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
