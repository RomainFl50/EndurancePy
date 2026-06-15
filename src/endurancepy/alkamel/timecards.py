"""Parser for the Al Kamel Time Cards CSV (``23_*``).

Time cards link each driver to the laps they drove, which is needed to attribute
laps to drivers within a multi-driver crew. Implementation lands in milestone 2.3.
"""

from __future__ import annotations

import pandas as pd


def map_drivers(raw: pd.DataFrame) -> pd.DataFrame:
    """Build a (car, lap) -> driver mapping from time cards. Not implemented yet."""
    raise NotImplementedError
