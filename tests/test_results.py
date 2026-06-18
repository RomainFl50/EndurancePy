"""Tests for building SessionResults from laps, and Session car helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import endurancepy as ep
from endurancepy.alkamel.analysis import read_analysis
from endurancepy.core import CarResult, Laps, SessionResults
from endurancepy.results import from_laps

FIXTURE = Path(__file__).parent / "fixtures" / "analysis_sample.csv"


@pytest.fixture
def laps() -> Laps:
    return read_analysis(FIXTURE)


@pytest.fixture
def results(laps: Laps) -> SessionResults:
    return from_laps(laps)


def _car(results: SessionResults, number: str) -> pd.Series:
    row = results[results["CarNumber"] == number]
    assert len(row) == 1
    return row.iloc[0]


def test_is_session_results_one_row_per_car(results: SessionResults) -> None:
    assert isinstance(results, SessionResults)
    assert len(results) == 3
    assert set(results["CarNumber"]) == {"7", "8", "83"}


def test_overall_finishing_order(results: SessionResults) -> None:
    assert _car(results, "8")["Position"] == 1
    assert _car(results, "7")["Position"] == 2
    assert _car(results, "83")["Position"] == 3


def test_in_class_positions(results: SessionResults) -> None:
    assert _car(results, "8")["PositionInClass"] == 1
    assert _car(results, "7")["PositionInClass"] == 2
    assert _car(results, "83")["PositionInClass"] == 1


def test_lap_counts_and_best_lap(results: SessionResults) -> None:
    assert _car(results, "7")["Laps"] == 4
    assert _car(results, "83")["Laps"] == 3
    assert _car(results, "7")["BestLapTime"] == pd.Timedelta(seconds=94.5)


def test_crew_metadata(results: SessionResults) -> None:
    assert _car(results, "7")["Crew"] == "A AAA; B BBB"
    assert _car(results, "8")["Crew"] == "C CCC"
    assert _car(results, "7")["Manufacturer"] == "Toyota"
    assert _car(results, "8")["TeamName"] == "AF Corse"
    assert _car(results, "83")["Class"] == "LMGT3"


def test_classified_position_strings(results: SessionResults) -> None:
    assert _car(results, "8")["ClassifiedPosition"] == "1"
    assert _car(results, "83")["ClassifiedPositionInClass"] == "1"


def test_counters_are_integers(results: SessionResults) -> None:
    # positions / laps are nullable integers, not floats ("2", not "2.0")
    for column in ("Position", "PositionInClass", "GridPosition", "Laps"):
        assert results[column].dtype == "Int64"
    assert str(_car(results, "7")["Position"]) == "2"
    assert str(_car(results, "7")["Laps"]) == "4"


def test_no_per_driver_columns(results: SessionResults) -> None:
    # the classification is per car/crew; individual driver fields are dropped
    for column in ("DriverNumber", "Abbreviation", "FirstName", "LastName", "FullName"):
        assert column not in results.columns


def test_pick_classes_on_results(results: SessionResults) -> None:
    assert set(results.pick_classes("HYPERCAR")["CarNumber"]) == {"7", "8"}


def test_session_derives_results_from_laps(laps: Laps) -> None:
    session = ep.get_session(2024, "WEC", "Le Mans", "Race")
    session._laps = laps  # injected until Session.load is implemented (2.5)
    assert session.cars == ["8", "7", "83"]
    car = session.get_car("7")
    assert isinstance(car, CarResult)
    assert car["Position"] == 2
    with pytest.raises(ValueError):
        session.get_car("99")
