"""Parser for the Al Kamel Weather CSV (``26_Weather_*.CSV``).

Verified real header (semicolon-separated)::

    TIME_UTC_SECONDS;TIME_UTC_STR;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;
    WIND_SPEED;WIND_DIRECTION;

Produces the same channels as FastF1's ``weather_data`` where available. ``Time``
is relative to the first sample (derived from ``TIME_UTC_SECONDS``); ``Rainfall``
is not provided by Al Kamel and is left empty.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from endurancepy._types import WEATHER_COLUMNS
from endurancepy.alkamel.headers import read_alkamel_csv


def read_weather(source: bytes | str | os.PathLike[str]) -> pd.DataFrame:
    """Read and parse a Weather CSV (bytes or path) into a weather DataFrame."""
    return to_weather(read_alkamel_csv(source))


def to_weather(raw: pd.DataFrame) -> pd.DataFrame:
    """Convert a normalised Weather DataFrame into FastF1-style ``weather_data``."""
    index = pd.RangeIndex(len(raw))

    def num(name: str) -> pd.Series:
        if name in raw.columns:
            return pd.to_numeric(raw[name].reset_index(drop=True), errors="coerce")
        return pd.Series(np.nan, index=index)

    epoch = num("TIME_UTC_SECONDS")
    if epoch.notna().any():
        time = pd.to_timedelta(epoch - epoch.min(), unit="s")
    else:
        time = pd.Series(pd.NaT, index=index, dtype="timedelta64[ns]")

    data = {
        "Time": time,
        "AirTemp": num("AIR_TEMP"),
        "TrackTemp": num("TRACK_TEMP"),
        "Humidity": num("HUMIDITY"),
        "Pressure": num("PRESSURE"),
        "Rainfall": pd.Series(pd.NA, index=index, dtype="boolean"),
        "WindSpeed": num("WIND_SPEED"),
        "WindDirection": num("WIND_DIRECTION"),
    }
    frame = pd.DataFrame(data)
    return frame.astype(WEATHER_COLUMNS)
