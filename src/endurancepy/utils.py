"""Small presentation helpers (formatting durations, etc.).

Lap and sector times are stored as :class:`pandas.Timedelta` (mirroring FastF1)
so they can be compared and aggregated. Their default text form is the verbose
``0 days 00:01:58.056000``; :func:`format_timedelta` renders the readable
``1:58.056`` (or ``H:MM:SS.mmm`` past the hour) for display.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

__all__ = ["format_laptime", "format_timedelta"]


def format_timedelta(value: Any, *, millis: bool = True) -> str:
    """Render a duration as ``M:SS.mmm`` (or ``H:MM:SS.mmm`` with hours).

    Parameters
    ----------
    value:
        A :class:`pandas.Timedelta`, :class:`datetime.timedelta`, or anything
        :func:`pandas.to_timedelta` accepts. Missing values give ``""``.
    millis:
        Include milliseconds (default ``True``).

    Examples
    --------
    >>> format_timedelta(pd.Timedelta("0 days 00:01:58.056"))
    '1:58.056'
    >>> format_timedelta(pd.Timedelta(hours=3, minutes=12, seconds=45))
    '3:12:45.000'
    """
    if value is None:
        return ""
    try:
        td = pd.to_timedelta(value)
    except (ValueError, TypeError):
        return ""
    if td is pd.NaT or pd.isna(td):
        return ""

    total_ms = round(td.total_seconds() * 1000)
    sign = "-" if total_ms < 0 else ""
    total_ms = abs(total_ms)
    ms = total_ms % 1000
    total_s = total_ms // 1000
    hours, rem = divmod(total_s, 3600)
    minutes, seconds = divmod(rem, 60)

    tail = f".{ms:03d}" if millis else ""
    if hours:
        return f"{sign}{hours}:{minutes:02d}:{seconds:02d}{tail}"
    return f"{sign}{minutes}:{seconds:02d}{tail}"


#: Alias of :func:`format_timedelta`, read naturally for lap times.
format_laptime = format_timedelta
