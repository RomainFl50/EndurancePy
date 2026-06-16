"""Parsing of Al Kamel time strings into pandas ``Timedelta`` values.

Times appear in several forms (``SS.mmm``, ``M:SS.mmm``, ``H:MM:SS.mmm``) and the
cumulative ``ELAPSED`` field can exceed 24 hours (e.g. ``24:01:02.345``), which a
plain clock parser would reject. A single colon-splitting parser handles all
cases; empty/invalid values become ``NaT``.
"""

from __future__ import annotations

import pandas as pd


def parse_duration(value: object) -> pd.Timedelta:
    """Parse a duration string (lap/sector time) into a ``Timedelta``.

    Accepts ``SS.mmm``, ``M:SS.mmm`` and ``H:MM:SS.mmm`` (hours may exceed 24).
    Returns ``pd.NaT`` for empty or unparseable values.
    """
    if value is None:
        return pd.NaT
    text = str(value).strip()
    if not text:
        return pd.NaT
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    parts = text.split(":")
    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        return pd.NaT
    if len(numbers) == 1:
        seconds = numbers[0]
    elif len(numbers) == 2:
        seconds = numbers[0] * 60 + numbers[1]
    elif len(numbers) == 3:
        seconds = numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
    else:
        return pd.NaT
    delta = pd.Timedelta(seconds=seconds)
    return -delta if negative else delta


def parse_elapsed(value: object) -> pd.Timedelta:
    """Parse a cumulative ``ELAPSED`` time, tolerating the >24h rollover."""
    return parse_duration(value)
