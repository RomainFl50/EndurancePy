"""Tolerant header handling for Al Kamel CSV files.

The Analysis CSV is semicolon-separated, UTF-8 **with BOM**, and the first ~15
header tokens carry a leading space (e.g. ``" DRIVER_NUMBER"``). The header also
drifts across seasons/series (older files lack ``Sn_SECONDS``/``FLAG_AT_FL``; the
IMSA "WithSections" variant adds intermediate-loop columns). Parsers must match
columns by their normalised name. Implementation lands in milestone 2.2.
"""

from __future__ import annotations

#: Encoding to use when reading Al Kamel CSV files (handles the BOM).
CSV_ENCODING = "utf-8-sig"

#: Field separator used by Al Kamel CSV files.
CSV_SEPARATOR = ";"


def normalize_header(name: str) -> str:
    """Normalise a raw CSV column name (strip BOM/whitespace, upper-case)."""
    return name.replace("﻿", "").strip().upper()


def normalize_headers(names: list[str]) -> list[str]:
    """Normalise a list of raw CSV column names."""
    return [normalize_header(n) for n in names]
