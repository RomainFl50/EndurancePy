"""Parser for the Al Kamel Classification CSV -> ``SessionResults``.

Targets the race classification layout (verified real header)::

    POSITION;NUMBER;TEAM;DRIVER_1;DRIVER_2;DRIVER_3;DRIVER_4;VEHICLE;TYRES;
    CLASS;GROUP;DIVISION;STATUS;LAPS;TOTAL_TIME;GAP_FIRST;GAP_PREVIOUS;
    FL_LAPNUM;FL_TIME;FL_KPH;DRIVER_5;

Times use an apostrophe for minutes (e.g. ``5:44'41.101``, ``1'58.056``). The
parser is tolerant: practice/qualifying classifications use a different, wider
schema, so missing columns are simply left empty. When a Classification CSV is
not available, results are instead derived from the laps (see
:mod:`endurancepy.results`).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from endurancepy._types import RESULTS_COLUMNS
from endurancepy.alkamel.headers import read_alkamel_csv
from endurancepy.alkamel.timeparse import parse_duration
from endurancepy.core import SessionResults

if TYPE_CHECKING:
    from endurancepy.core import Session

_DRIVER_COLUMNS = ["DRIVER_1", "DRIVER_2", "DRIVER_3", "DRIVER_4", "DRIVER_5"]


def _empty_column(dtype: str, index: pd.Index) -> pd.Series:
    if dtype.startswith("timedelta"):
        return pd.Series(pd.NaT, index=index, dtype="timedelta64[ns]")
    if dtype.startswith("datetime"):
        return pd.Series(pd.NaT, index=index, dtype="datetime64[ns]")
    if dtype == "float64":
        return pd.Series(np.nan, index=index, dtype="float64")
    if dtype == "boolean":
        return pd.Series(pd.NA, index=index, dtype="boolean")
    return pd.Series(pd.NA, index=index, dtype="string")


def _parse_clock(value: object) -> pd.Timedelta:
    """Parse an Al Kamel classification time (minutes use an apostrophe)."""
    return parse_duration(str(value).replace("'", ":"))


def read_classification(
    source: bytes | str | os.PathLike[str], *, session: Session | None = None
) -> SessionResults:
    """Read and parse a Classification CSV (bytes or path) into ``SessionResults``."""
    return to_results(read_alkamel_csv(source), session=session)


def to_results(raw: pd.DataFrame, *, session: Session | None = None) -> SessionResults:
    """Convert a normalised Classification DataFrame into ``SessionResults``."""
    cols = set(raw.columns)

    def get(*names: str) -> pd.Series | None:
        for name in names:
            if name in cols:
                return raw[name].reset_index(drop=True)
        return None

    if len(raw) == 0:
        empty = {
            name: _empty_column(dtype, pd.RangeIndex(0))
            for name, dtype in RESULTS_COLUMNS.items()
        }
        return SessionResults(empty, session=session)

    index = pd.RangeIndex(len(raw))

    def text(series: pd.Series | None) -> pd.Series:
        if series is None:
            return pd.Series(pd.NA, index=index, dtype="string")
        return series.replace("", pd.NA).astype("string")

    def clock(series: pd.Series | None) -> pd.Series:
        if series is None:
            return pd.Series(pd.NaT, index=index, dtype="timedelta64[ns]")
        return pd.to_timedelta(series.map(_parse_clock))

    position = pd.to_numeric(get("POSITION", "POS"), errors="coerce").astype("float64")

    driver_cols = [c for c in _DRIVER_COLUMNS if c in cols]
    if driver_cols:
        crew = (
            raw[driver_cols]
            .apply(
                lambda row: "; ".join(
                    v for v in row if isinstance(v, str) and v.strip()
                ),
                axis=1,
            )
            .reset_index(drop=True)
        )
    else:
        crew = pd.Series("", index=index)

    vehicle = get("VEHICLE")
    manufacturer = get("MANUFACTURER")
    if manufacturer is None and vehicle is not None:
        manufacturer = vehicle.map(
            lambda v: v.split()[0] if isinstance(v, str) and v.strip() else pd.NA
        )

    summary = pd.DataFrame(
        {
            "CarNumber": text(get("NUMBER")),
            "Class": text(get("CLASS")),
            "Manufacturer": text(manufacturer),
            "TeamName": text(get("TEAM")),
            "Crew": crew.astype("string"),
            "Position": position,
            "Time": clock(get("TOTAL_TIME")),
            "BestLapTime": clock(get("FL_TIME", "TIME")),
            "Status": text(get("STATUS")),
            "Laps": pd.to_numeric(get("LAPS"), errors="coerce").astype("float64"),
        }
    )
    summary = summary.sort_values("Position").reset_index(drop=True)
    summary["PositionInClass"] = (
        summary.groupby("Class", sort=False).cumcount() + 1
    ).astype("float64")
    summary["ClassifiedPosition"] = summary["Position"].map(
        lambda p: str(int(p)) if pd.notna(p) else pd.NA
    )
    summary["ClassifiedPositionInClass"] = summary["PositionInClass"].map(
        lambda p: str(int(p)) if pd.notna(p) else pd.NA
    )

    columns: dict[str, pd.Series] = {}
    for name, dtype in RESULTS_COLUMNS.items():
        if name in summary.columns:
            columns[name] = summary[name].reset_index(drop=True).astype(dtype)
        else:
            columns[name] = _empty_column(dtype, pd.RangeIndex(len(summary)))
    return SessionResults(columns, session=session)
