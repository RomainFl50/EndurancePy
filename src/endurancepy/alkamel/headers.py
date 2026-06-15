"""Tolerant reading of Al Kamel CSV files.

The Analysis CSV is semicolon-separated, UTF-8 **with BOM**, and the first ~15
header tokens carry a leading space (e.g. ``" DRIVER_NUMBER"``). The header also
drifts across seasons/series (older files lack ``Sn_SECONDS``/``FLAG_AT_FL``; the
IMSA "WithSections" variant adds intermediate-loop columns) and the rows have a
trailing separator (an empty final column). Reading therefore: uses the
``utf-8-sig`` encoding, keeps every value as a stripped string, normalises header
names, and drops empty/unnamed columns. Parsers then match columns by name.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd

#: Encoding to use when reading Al Kamel CSV files (handles the BOM).
CSV_ENCODING = "utf-8-sig"

#: Field separator used by Al Kamel CSV files.
CSV_SEPARATOR = ";"


def normalize_header(name: str) -> str:
    """Normalise a raw CSV column name (strip BOM/whitespace, upper-case)."""
    return name.replace("﻿", "").strip().upper()


def normalize_headers(names: list[str]) -> list[str]:
    """Normalise a list of raw CSV column names."""
    return [normalize_header(name) for name in names]


def read_alkamel_csv(source: bytes | str | os.PathLike[str]) -> pd.DataFrame:
    """Read an Al Kamel CSV into a DataFrame of stripped strings.

    Parameters
    ----------
    source:
        Raw file bytes, or a path to a file on disk.

    Returns
    -------
    pandas.DataFrame
        All values as stripped strings; columns normalised (upper-case, no BOM
        or surrounding spaces); empty/unnamed trailing columns dropped.
    """
    buffer: io.BytesIO | Path
    if isinstance(source, (bytes, bytearray)):
        buffer = io.BytesIO(bytes(source))
    else:
        buffer = Path(source)

    frame = pd.read_csv(
        buffer,
        sep=CSV_SEPARATOR,
        dtype=str,
        encoding=CSV_ENCODING,
        keep_default_na=False,
        na_filter=False,
    )
    frame.columns = pd.Index(normalize_headers(list(frame.columns)))
    # Drop empty/unnamed columns (e.g. from the trailing separator).
    keep = [col for col in frame.columns if col and not col.startswith("UNNAMED")]
    frame = frame.loc[:, keep]
    # Strip every value.
    for col in frame.columns:
        frame[col] = frame[col].str.strip()
    return frame
