"""Tests for the Al Kamel race Classification CSV parser (verified format)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import endurancepy as ep
from endurancepy._types import RESULTS_COLUMNS
from endurancepy.alkamel.classification import read_classification
from endurancepy.cache import Cache
from endurancepy.core import SessionResults

FIXTURE = Path(__file__).parent / "fixtures" / "classification_race_sample.csv"
LAPS_FIXTURE = Path(__file__).parent / "fixtures" / "analysis_sample.csv"


@pytest.fixture
def results() -> SessionResults:
    return read_classification(FIXTURE)


def _car(results: SessionResults, number: str) -> pd.Series:
    row = results[results["CarNumber"] == number]
    assert len(row) == 1
    return row.iloc[0]


def test_is_session_results(results: SessionResults) -> None:
    assert isinstance(results, SessionResults)
    assert len(results) == 4
    assert list(results.columns) == list(RESULTS_COLUMNS)


def test_positions_and_status(results: SessionResults) -> None:
    assert _car(results, "8")["Position"] == 1
    assert _car(results, "8")["Status"] == "Classified"
    assert _car(results, "8")["Laps"] == 133


def test_total_time_apostrophe_format(results: SessionResults) -> None:
    assert _car(results, "8")["Time"] == pd.Timedelta(
        hours=5, minutes=44, seconds=41.101
    )


def test_best_lap_time(results: SessionResults) -> None:
    assert _car(results, "8")["BestLapTime"] == pd.Timedelta(minutes=1, seconds=58.056)


def test_crew_and_manufacturer(results: SessionResults) -> None:
    assert (
        _car(results, "8")["Crew"]
        == "Sebastien BUEMI; Kazuki NAKAJIMA; Fernando ALONSO"
    )
    assert _car(results, "8")["Manufacturer"] == "Toyota"
    assert _car(results, "8")["TeamName"] == "Toyota Gazoo Racing"


def test_in_class_positions(results: SessionResults) -> None:
    assert _car(results, "8")["PositionInClass"] == 1
    assert _car(results, "7")["PositionInClass"] == 2
    assert _car(results, "17")["PositionInClass"] == 3
    assert _car(results, "91")["PositionInClass"] == 1  # only LMGTE Pro car


def test_session_load_results_source(tmp_path: Path) -> None:
    Cache.enable_cache(tmp_path)
    session = ep.get_session(2019, "WEC", "Spa", "Race")
    session.load(source=LAPS_FIXTURE, results_source=FIXTURE)
    # results come from the classification file (car 8 leads), not the laps
    assert session.results.iloc[0]["CarNumber"] == "8"
    assert len(session.laps) == 11  # laps still loaded
