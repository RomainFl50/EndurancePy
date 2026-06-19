"""Tests for the Al Kamel Analysis CSV parser (offline, synthetic fixture)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from endurancepy._types import LAPS_COLUMNS, LAPS_COMPAT_COLUMNS
from endurancepy.alkamel.analysis import read_analysis
from endurancepy.core import Lap, Laps

FIXTURE = Path(__file__).parent / "fixtures" / "analysis_sample.csv"


@pytest.fixture
def laps() -> Laps:
    return read_analysis(FIXTURE)


def _row(laps: Laps, car: str, lap: int) -> pd.Series:
    subset = laps[(laps["CarNumber"] == car) & (laps["LapNumber"] == lap)]
    assert len(subset) == 1
    return subset.iloc[0]


def test_returns_laps_with_all_rows(laps: Laps) -> None:
    assert isinstance(laps, Laps)
    assert len(laps) == 11


def test_columns_match_schema(laps: Laps) -> None:
    expected = list({**LAPS_COLUMNS, **LAPS_COMPAT_COLUMNS})
    assert list(laps.columns) == expected


def test_car_numbers_kept_as_strings(laps: Laps) -> None:
    assert set(laps["CarNumber"].unique()) == {"7", "8", "83"}


def test_lap_and_sector_times(laps: Laps) -> None:
    row = _row(laps, "7", 1)
    assert row["LapTime"] == pd.Timedelta(seconds=95)
    assert row["Sector1Time"] == pd.Timedelta(seconds=28)
    assert row["Sector1SessionTime"] == pd.Timedelta(seconds=28)
    assert row["Sector3SessionTime"] == pd.Timedelta(seconds=95)


def test_speeds_average_vs_top(laps: Laps) -> None:
    row = _row(laps, "7", 1)
    assert row["LapAvgSpeed"] == 175.0  # KPH = average lap speed
    assert row["SpeedST"] == 300.0  # TOP_SPEED = speed-trap peak


def test_stints_and_pit_times(laps: Laps) -> None:
    assert _row(laps, "7", 1)["Stint"] == 1
    assert _row(laps, "7", 2)["Stint"] == 1
    assert _row(laps, "7", 3)["Stint"] == 2
    assert _row(laps, "7", 4)["Stint"] == 2
    assert pd.notna(_row(laps, "7", 2)["PitInTime"])
    assert pd.notna(_row(laps, "7", 3)["PitOutTime"])
    assert pd.isna(_row(laps, "7", 1)["PitInTime"])


def test_driver_change(laps: Laps) -> None:
    assert bool(_row(laps, "7", 3)["DriverChange"]) is True
    assert bool(_row(laps, "7", 1)["DriverChange"]) is False


def test_personal_best(laps: Laps) -> None:
    assert bool(_row(laps, "7", 4)["IsPersonalBest"]) is True
    assert bool(_row(laps, "7", 1)["IsPersonalBest"]) is False


def test_accuracy(laps: Laps) -> None:
    assert bool(_row(laps, "7", 1)["IsAccurate"]) is True
    assert bool(_row(laps, "7", 2)["IsAccurate"]) is False  # in-lap
    assert bool(_row(laps, "7", 3)["IsAccurate"]) is False  # out-lap
    assert bool(_row(laps, "8", 3)["IsAccurate"]) is False  # FCY


def test_overall_positions(laps: Laps) -> None:
    assert _row(laps, "7", 1)["Position"] == 1
    assert _row(laps, "8", 1)["Position"] == 2
    assert _row(laps, "83", 1)["Position"] == 3
    assert _row(laps, "8", 4)["Position"] == 1
    assert _row(laps, "7", 4)["Position"] == 2


def test_in_class_positions(laps: Laps) -> None:
    assert _row(laps, "83", 1)["PositionInClass"] == 1
    assert _row(laps, "8", 4)["PositionInClass"] == 1
    assert _row(laps, "7", 4)["PositionInClass"] == 2


def test_pick_cars_and_classes(laps: Laps) -> None:
    assert set(laps.pick_cars("7")["CarNumber"].unique()) == {"7"}
    assert set(laps.pick_classes("HYPERCAR")["Class"].unique()) == {"HYPERCAR"}
    assert len(laps.pick_classes("LMGT3")) == 3


def test_pick_box_and_wo_box(laps: Laps) -> None:
    assert len(laps.pick_box_laps("in")) == 1
    assert len(laps.pick_box_laps("out")) == 1
    assert len(laps.pick_wo_box()) == 9


def test_pick_fastest_uses_personal_best(laps: Laps) -> None:
    fastest = laps.pick_classes("HYPERCAR").pick_fastest()
    assert isinstance(fastest, Lap)
    assert fastest["CarNumber"] == "7"
    assert fastest["LapNumber"] == 4
    assert fastest["LapTime"] == pd.Timedelta(seconds=94.5)


def test_pick_accurate(laps: Laps) -> None:
    accurate = laps.pick_accurate()
    assert len(accurate) == 8
    assert bool(accurate["IsAccurate"].all())


def test_pit_time_kept_on_in_lap(laps: Laps) -> None:
    assert _row(laps, "7", 2)["PitTime"] == pd.Timedelta(seconds=30)  # the pit-in lap
    assert pd.isna(_row(laps, "7", 1)["PitTime"])  # no stop on other laps


def test_gap_to_leader(laps: Laps) -> None:
    # On lap 1: car 7 leads (95.0s), car 8 is +1s, car 83 (other class) +15s.
    assert _row(laps, "7", 1)["GapToLeader"] == pd.Timedelta(0)
    assert _row(laps, "8", 1)["GapToLeader"] == pd.Timedelta(seconds=1)
    assert _row(laps, "83", 1)["GapToLeader"] == pd.Timedelta(seconds=15)
    # The leader's gap is zero at every lap (overall and per class).
    by_lap = laps.groupby("LapNumber")["GapToLeader"].min()
    assert (by_lap == pd.Timedelta(0)).all()
    assert _row(laps, "83", 1)["GapToLeaderInClass"] == pd.Timedelta(0)  # LMGT3 leader
