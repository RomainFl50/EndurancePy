"""Parser for the Al Kamel "Analysis" CSV (``23_Analysis*.CSV``) -> ``Laps``.

This is the primary data product: one row per car-lap, with lap/sector times,
average and top speed, pit indicator, class/team/manufacturer, and the flag at
the finish line. Derived columns (stint, pit in/out, lap start time, overall and
in-class position, gaps, accuracy) are computed here. Implementation lands in
milestone 2.2 — the core of the project.
"""

from __future__ import annotations

import pandas as pd

from endurancepy.core import Laps


def to_laps(raw: pd.DataFrame) -> Laps:
    """Convert a parsed Analysis CSV into a :class:`~endurancepy.core.Laps`.

    Not implemented yet (milestone 2.2).
    """
    raise NotImplementedError
