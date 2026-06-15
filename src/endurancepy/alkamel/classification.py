"""Parser for the Al Kamel Classification CSV (``03_*``) -> ``SessionResults``.

Provides the per-car/crew classification, both overall and per class.
Implementation lands in milestone 2.3.
"""

from __future__ import annotations

import pandas as pd

from endurancepy.core import SessionResults


def to_results(raw: pd.DataFrame) -> SessionResults:
    """Convert a parsed Classification CSV into ``SessionResults``. Not done."""
    raise NotImplementedError
