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
