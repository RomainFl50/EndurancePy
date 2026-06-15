"""Parser for the Al Kamel Weather CSV (``26_*``) -> weather ``DataFrame``.

Produces the same channels as FastF1's ``weather_data`` (air/track temperature,
humidity, pressure, rainfall, wind speed/direction). Implementation lands in
milestone 2.4.
"""

from __future__ import annotations

import pandas as pd


def to_weather(raw: pd.DataFrame) -> pd.DataFrame:
    """Convert a parsed Weather CSV into a weather ``DataFrame``. Not implemented."""
    raise NotImplementedError
