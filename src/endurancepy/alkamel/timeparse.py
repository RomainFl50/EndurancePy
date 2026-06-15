"""Parsing of Al Kamel time strings into pandas ``Timedelta`` values.

Times appear in several forms (``SS.mmm``, ``M:SS.mmm``, ``H:MM:SS.mmm``) and the
cumulative ``ELAPSED`` field can exceed 24 hours (``24:`` rollover). A robust
single parser is provided here. Implementation lands in milestone 2.2.
"""

from __future__ import annotations

import pandas as pd


def parse_duration(value: str) -> pd.Timedelta:
    """Parse a lap/sector duration string into a ``Timedelta``. Not implemented."""
    raise NotImplementedError


def parse_elapsed(value: str) -> pd.Timedelta:
    """Parse a cumulative ``ELAPSED`` time, handling the 24h rollover. Not done."""
    raise NotImplementedError
