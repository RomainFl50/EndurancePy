"""Build a session classification (``SessionResults``) from lap data.

There is no *verified* public column layout for the Al Kamel Classification CSV,
so rather than parse an unverified format, EndurancePy reconstructs the final
classification from the (reliable) Analysis-derived :class:`~endurancepy.core.Laps`:
final order by laps completed then total time, per overall and per class, plus
each car's crew, best lap and lap count. A dedicated Classification-CSV parser
can be added later once its format is confirmed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from endurancepy._types import RESULTS_COLUMNS
from endurancepy.core import Laps, SessionResults

if TYPE_CHECKING:
    from endurancepy.core import Session


def _empty_column(dtype: str, index: pd.Index) -> pd.Series:
    if dtype.startswith("timedelta"):
        return pd.Series(pd.NaT, index=index, dtype="timedelta64[ns]")
    if dtype.startswith("datetime"):
        return pd.Series(pd.NaT, index=index, dtype="datetime64[ns]")
    if dtype == "float64":
        return pd.Series(np.nan, index=index, dtype="float64")
    if dtype == "Int64":
        return pd.Series(pd.NA, index=index, dtype="Int64")
    if dtype == "boolean":
        return pd.Series(pd.NA, index=index, dtype="boolean")
    return pd.Series(pd.NA, index=index, dtype="string")


def from_laps(laps: Laps, *, session: Session | None = None) -> SessionResults:
    """Reconstruct a :class:`SessionResults` from a :class:`Laps` table.

    Cars are ranked by laps completed (descending) then total time (ascending),
    both overall and within each class.
    """
    if len(laps) == 0:
        empty = {
            name: _empty_column(dtype, pd.RangeIndex(0))
            for name, dtype in RESULTS_COLUMNS.items()
        }
        return SessionResults(empty, session=session)

    frame = pd.DataFrame(laps)
    rows = []
    for car, group in frame.groupby("CarNumber", sort=False):
        group = group.sort_values("LapNumber")
        last = group.iloc[-1]
        drivers = dict.fromkeys(group["Driver"].dropna().astype(str))
        rows.append(
            {
                "CarNumber": car,
                "Class": last["Class"],
                "Manufacturer": last["Manufacturer"],
                "TeamName": last["Team"],
                "Crew": "; ".join(drivers),
                "Time": last["Time"],
                "BestLapTime": group["LapTime"].min(),
                "Laps": int(group["LapNumber"].max()),
                "Status": "Finished",
            }
        )

    summary = pd.DataFrame(rows)
    summary = summary.sort_values(
        ["Laps", "Time"], ascending=[False, True]
    ).reset_index(drop=True)
    summary["Position"] = summary.index + 1
    summary["PositionInClass"] = summary.groupby("Class", sort=False).cumcount() + 1
    summary["ClassifiedPosition"] = summary["Position"].astype(str)
    summary["ClassifiedPositionInClass"] = summary["PositionInClass"].astype(str)

    index = pd.RangeIndex(len(summary))
    columns: dict[str, pd.Series] = {}
    for name, dtype in RESULTS_COLUMNS.items():
        if name in summary.columns:
            columns[name] = summary[name].reset_index(drop=True).astype(dtype)
        else:
            columns[name] = _empty_column(dtype, index)
    return SessionResults(columns, session=session)
