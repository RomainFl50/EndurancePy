"""Reconstruct the track-status (flag) timeline from lap data.

The Analysis CSV records the flag in force as each car crossed the finish line
(``FLAG_AT_FL``). Collapsing those crossings into a chronological sequence of
flag *changes* yields a session-wide track-status timeline, similar to FastF1's
``Session.track_status`` but with endurance-specific states (FCY, Code 60, slow
zones) in addition to green/SC/red.
"""

from __future__ import annotations

import pandas as pd

from endurancepy._types import TRACK_STATUS_COLUMNS
from endurancepy.core import Laps

#: Map raw Al Kamel finish-line flags to readable statuses.
FLAG_STATUS: dict[str, str] = {
    "GF": "GreenFlag",
    "FCY": "FullCourseYellow",
    "SC": "SafetyCar",
    "SF": "SlowZone",
    "FF": "Chequered",
    "CODE60": "Code60",
    "C60": "Code60",
    "YF": "Yellow",
    "YEL": "Yellow",
    "YELLOW": "Yellow",
    "RF": "RedFlag",
    "RED": "RedFlag",
}


def status_for_flag(flag: str) -> str:
    """Map a raw flag code (e.g. ``"FCY"``) to a readable status."""
    return FLAG_STATUS.get(str(flag).upper(), str(flag).upper())


def from_laps(laps: Laps) -> pd.DataFrame:
    """Build the track-status timeline (one row per flag change) from laps."""
    empty = {
        name: pd.Series(dtype=dtype) for name, dtype in TRACK_STATUS_COLUMNS.items()
    }
    if len(laps) == 0:
        return pd.DataFrame(empty)

    events = pd.DataFrame(laps)[["Time", "TrackStatus"]]
    events = events.dropna(subset=["Time"])
    events = events[events["TrackStatus"].notna()]
    if len(events) == 0:
        return pd.DataFrame(empty)
    events = events.sort_values("Time", kind="stable")

    status = events["TrackStatus"]
    changed = status.ne(status.shift()).fillna(True).astype(bool)
    changes = events[changed].reset_index(drop=True)
    return pd.DataFrame(
        {
            "Time": changes["Time"].astype("timedelta64[ns]"),
            "Status": changes["TrackStatus"].map(status_for_flag).astype("string"),
            "Message": changes["TrackStatus"].astype("string"),
        }
    )
