"""Tests for strategy analysis derived from the laps (offline, synthetic fixture)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import endurancepy as ep
from endurancepy.alkamel.analysis import read_analysis
from endurancepy.core import Laps

FIXTURE = Path(__file__).parent / "fixtures" / "analysis_sample.csv"


def _laps() -> Laps:
    return read_analysis(FIXTURE)


def test_pit_stops_one_row_per_stop() -> None:
    stops = ep.pit_stops(_laps())
    # only car 7 pits in the fixture (lap 2, ending stint 1, 30s in the pits)
    assert len(stops) == 1
    stop = stops.iloc[0]
    assert stop["CarNumber"] == "7"
    assert stop["Lap"] == 2
    assert stop["Stint"] == 1
    assert stop["PitTime"] == pd.Timedelta(seconds=30)
    assert stop["Class"] == "HYPERCAR"
    assert stop["TeamName"] == "Toyota Gazoo Racing"


def test_pit_stops_dtypes_and_order() -> None:
    stops = ep.pit_stops(_laps())
    assert stops["Lap"].dtype == "Int64"
    assert stops["Stint"].dtype == "Int64"
    assert list(stops.columns) == [
        "CarNumber",
        "Lap",
        "Stint",
        "PitTime",
        "Class",
        "Manufacturer",
        "TeamName",
    ]


def test_pit_stops_empty_laps() -> None:
    stops = ep.pit_stops(_laps().iloc[0:0])
    assert stops.empty
    assert "PitTime" in stops.columns  # still a well-formed (empty) table


def _stint(table: pd.DataFrame, car: str, stint: int) -> pd.Series:
    row = table[(table["CarNumber"] == car) & (table["Stint"] == stint)]
    assert len(row) == 1
    return row.iloc[0]


def test_stint_summary() -> None:
    stints = ep.stint_summary(_laps())
    assert len(stints) == 4  # car 7 has 2 stints; cars 8 and 83 one each
    # car 8's single 4-lap stint: pace + a (negative = improving) degradation slope
    car8 = _stint(stints, "8", 1)
    assert car8["Driver"] == "C CCC"
    assert car8["Laps"] == 4
    assert car8["BestLap"] == pd.Timedelta(seconds=95)
    assert pd.notna(car8["Degradation"]) and car8["Degradation"] < 0
    # car 7's first stint has a single clean lap -> no degradation slope
    car7 = _stint(stints, "7", 1)
    assert car7["Driver"] == "A AAA"
    assert pd.isna(car7["Degradation"])


def test_driver_summary() -> None:
    drivers = ep.driver_summary(_laps())
    assert set(drivers["Driver"]) == {"A AAA", "B BBB", "C CCC", "D DDD"}
    c = drivers[drivers["Driver"] == "C CCC"].iloc[0]
    assert c["Laps"] == 4
    assert c["TimeInCar"] == pd.Timedelta(seconds=381.7)  # 96+95.5+95+95.2
    assert c["BestLap"] == pd.Timedelta(seconds=95)
    assert pd.notna(c["Consistency"]) and c["Consistency"] > 0
    # a one-clean-lap driver has no consistency figure
    a = drivers[drivers["Driver"] == "A AAA"].iloc[0]
    assert a["Laps"] == 2
    assert pd.isna(a["Consistency"])


def test_lead_changes_overall() -> None:
    leads = ep.lead_changes(_laps())
    # car 7 leads lap 1, then car 8 takes over for laps 2-4 (one lead change)
    assert list(leads["Leader"]) == ["7", "8"]
    assert list(leads["FromLap"]) == [1, 2]
    assert list(leads["ToLap"]) == [1, 4]
    assert list(leads["Laps"]) == [1, 3]


def test_lead_changes_in_class() -> None:
    leads = ep.lead_changes(_laps(), in_class=True)
    lmgt3 = leads[leads["Class"] == "LMGT3"]
    assert len(lmgt3) == 1  # car 83 leads its class throughout
    assert lmgt3.iloc[0]["Leader"] == "83"
    assert lmgt3.iloc[0]["Laps"] == 3
    # HYPERCAR still has the 7 -> 8 change
    assert list(leads[leads["Class"] == "HYPERCAR"]["Leader"]) == ["7", "8"]


def test_summaries_empty_laps() -> None:
    empty = _laps().iloc[0:0]
    assert ep.stint_summary(empty).empty
    assert ep.driver_summary(empty).empty
    assert ep.lead_changes(empty).empty
