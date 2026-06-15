"""Parser for the Al Kamel "Analysis" CSV (``23_Analysis*.CSV``) -> ``Laps``.

This is the primary data product: one row per car-lap, with lap/sector times,
average and top speed, a pit indicator, class/team/manufacturer, and the flag at
the finish line. From these raw fields a number of FastF1-style columns are
derived here:

* ``Stint`` (segment between pit stops) and ``PitInTime`` / ``PitOutTime``
* ``LapStartTime`` and the cumulative ``SectorNSessionTime`` columns
* ``Position`` and ``PositionInClass`` (reconstructed from line crossings)
* ``IsPersonalBest``, ``IsAccurate`` and ``DriverChange``

Gaps (``GapToLeader*``), ``Hour`` and ``LapStartDate`` need session-level
context and are left empty here; they are filled in a later step.

See ``docs/analyse_fastf1.md`` §14.4 for the verified CSV format.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from endurancepy._types import LAPS_COLUMNS, LAPS_COMPAT_COLUMNS
from endurancepy.alkamel.headers import read_alkamel_csv
from endurancepy.alkamel.timeparse import parse_duration
from endurancepy.core import Laps

if TYPE_CHECKING:
    from endurancepy.core import Session

#: Tolerance for the "sum of sectors ≈ lap time" accuracy check.
_SECTOR_SUM_TOLERANCE = pd.Timedelta(seconds=0.5)


def read_analysis(
    source: bytes | str | os.PathLike[str], *, session: Session | None = None
) -> Laps:
    """Read and parse an Analysis CSV file (bytes or path) into ``Laps``."""
    return to_laps(read_alkamel_csv(source), session=session)


def to_laps(raw: pd.DataFrame, *, session: Session | None = None) -> Laps:
    """Convert a normalised Analysis DataFrame into a :class:`Laps`."""
    n = len(raw)
    index = pd.RangeIndex(n)

    def text(name: str) -> pd.Series:
        if name in raw.columns:
            return raw[name].reset_index(drop=True).replace("", pd.NA).astype("string")
        return pd.Series(pd.NA, index=index, dtype="string")

    def number(name: str) -> pd.Series:
        if name in raw.columns:
            return pd.to_numeric(raw[name].reset_index(drop=True), errors="coerce")
        return pd.Series(np.nan, index=index)

    def duration(name: str) -> pd.Series:
        if name in raw.columns:
            return pd.to_timedelta(raw[name].reset_index(drop=True).map(parse_duration))
        return pd.Series(pd.NaT, index=index, dtype="timedelta64[ns]")

    def sector(idx: int) -> pd.Series:
        seconds_col = f"S{idx}_SECONDS"
        if seconds_col in raw.columns:
            return pd.to_timedelta(number(seconds_col), unit="s")
        return duration(f"S{idx}")

    df = pd.DataFrame(index=index)
    df["CarNumber"] = text("NUMBER")
    df["DriverNumber"] = text("DRIVER_NUMBER")
    df["Driver"] = text("DRIVER_NAME")
    df["Team"] = text("TEAM")
    df["Class"] = text("CLASS")
    df["Manufacturer"] = text("MANUFACTURER")
    df["LapNumber"] = number("LAP_NUMBER").astype("float64")
    df["LapTime"] = duration("LAP_TIME")
    df["Sector1Time"] = sector(1)
    df["Sector2Time"] = sector(2)
    df["Sector3Time"] = sector(3)
    df["Time"] = duration("ELAPSED")
    df["SpeedST"] = number("TOP_SPEED").astype("float64")
    df["LapAvgSpeed"] = number("KPH").astype("float64")
    df["TrackStatus"] = text("FLAG_AT_FL")
    df["IsPersonalBest"] = number("LAP_IMPROVEMENT").isin([1, 2])

    # Helper columns (dropped before returning).
    crossing = (
        raw["CROSSING_FINISH_LINE_IN_PIT"].reset_index(drop=True).str.upper()
        if "CROSSING_FINISH_LINE_IN_PIT" in raw.columns
        else pd.Series("", index=index)
    )
    df["_PitTime"] = duration("PIT_TIME")
    df["_Pitted"] = (crossing == "B") | df["_PitTime"].notna()

    # Order per car/lap so the shift-based derivations are correct.
    df = df.sort_values(["CarNumber", "LapNumber"]).reset_index(drop=True)

    _derive_stints_and_pits(df)
    _derive_sector_session_times(df)
    _derive_driver_change(df)
    _derive_positions(df)
    _derive_accuracy(df)

    df = df.drop(columns=["_PitTime", "_Pitted"])
    return _finalize(df, session=session)


def _derive_stints_and_pits(df: pd.DataFrame) -> None:
    pitted = df["_Pitted"]
    car = df["CarNumber"]
    # A new stint starts on the lap *after* a pit-in lap.
    df["Stint"] = (
        pitted.groupby(car).transform(lambda s: s.shift(fill_value=False).cumsum()) + 1
    ).astype("float64")
    df["PitInTime"] = df["Time"].where(pitted)
    df["LapStartTime"] = df["Time"] - df["LapTime"]
    stint_start = df.groupby("CarNumber")["Stint"].transform(lambda s: s != s.shift())
    df["PitOutTime"] = df["LapStartTime"].where(stint_start & (df["Stint"] > 1))


def _derive_sector_session_times(df: pd.DataFrame) -> None:
    df["Sector3SessionTime"] = df["Time"]
    df["Sector2SessionTime"] = df["Time"] - df["Sector3Time"]
    df["Sector1SessionTime"] = df["Time"] - df["Sector3Time"] - df["Sector2Time"]


def _derive_driver_change(df: pd.DataFrame) -> None:
    def changed(s: pd.Series) -> pd.Series:
        return (s != s.shift()) & s.shift().notna()

    df["DriverChange"] = df.groupby("CarNumber")["DriverNumber"].transform(changed)


def _derive_positions(df: pd.DataFrame) -> None:
    """Reconstruct overall and in-class position at each line crossing."""
    car_class = dict(zip(df["CarNumber"], df["Class"], strict=False))
    laps_done: dict[object, float] = {}
    last_time: dict[object, pd.Timedelta] = {}
    position = pd.Series(np.nan, index=df.index, dtype="float64")
    position_in_class = pd.Series(np.nan, index=df.index, dtype="float64")

    order = df.sort_values("Time", kind="stable")
    for idx in order.index:
        car = df.at[idx, "CarNumber"]
        lap = df.at[idx, "LapNumber"]
        time = df.at[idx, "Time"]
        if pd.isna(time) or pd.isna(lap):
            continue
        laps_done[car] = lap
        last_time[car] = time
        cls = car_class.get(car)
        rank = 1
        rank_in_class = 1
        for other, other_lap in laps_done.items():
            if other == car:
                continue
            other_time = last_time[other]
            ahead = (other_lap > lap) or (other_lap == lap and other_time < time)
            if ahead:
                rank += 1
                if car_class.get(other) == cls:
                    rank_in_class += 1
        position.at[idx] = rank
        position_in_class.at[idx] = rank_in_class

    df["Position"] = position
    df["PositionInClass"] = position_in_class


def _derive_accuracy(df: pd.DataFrame) -> None:
    sector_sum = df[["Sector1Time", "Sector2Time", "Sector3Time"]].sum(
        axis=1, min_count=3
    )
    consistent = (df["LapTime"] - sector_sum).abs() <= _SECTOR_SUM_TOLERANCE
    flag = df["TrackStatus"].fillna("").str.upper()
    accurate = (
        df["LapTime"].notna()
        & df["PitInTime"].isna()
        & df["PitOutTime"].isna()
        & (flag == "GF")
        & (consistent | sector_sum.isna())
    )
    df["IsAccurate"] = accurate


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


def _finalize(df: pd.DataFrame, *, session: Session | None) -> Laps:
    schema = {**LAPS_COLUMNS, **LAPS_COMPAT_COLUMNS}
    df["Generated"] = False
    columns: dict[str, pd.Series] = {}
    for name, dtype in schema.items():
        series = df[name] if name in df.columns else _empty_column(dtype, df.index)
        columns[name] = series.astype(dtype)
    return Laps(columns, session=session)
