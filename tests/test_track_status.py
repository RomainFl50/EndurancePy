"""Tests for the track-status timeline derived from laps."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import endurancepy as ep
from endurancepy.alkamel.analysis import read_analysis
from endurancepy.core import Laps
from endurancepy.track_status import from_laps, status_for_flag

FIXTURE = Path(__file__).parent / "fixtures" / "analysis_sample.csv"


@pytest.fixture
def laps() -> Laps:
    return read_analysis(FIXTURE)


def test_status_for_flag_mapping() -> None:
    assert status_for_flag("GF") == "GreenFlag"
    assert status_for_flag("fcy") == "FullCourseYellow"
    assert status_for_flag("C60") == "Code60"
    assert status_for_flag("ZZ") == "ZZ"  # unknown passes through (upper-cased)


def test_timeline_columns(laps: Laps) -> None:
    ts = from_laps(laps)
    assert list(ts.columns) == ["Time", "Status", "Message"]


def test_timeline_collapses_to_changes(laps: Laps) -> None:
    ts = from_laps(laps)
    # The fixture is green throughout except one FCY lap, so: GF -> FCY -> GF.
    assert list(ts["Status"]) == ["GreenFlag", "FullCourseYellow", "GreenFlag"]
    assert ts.iloc[1]["Message"] == "FCY"
    assert ts.iloc[1]["Time"] == pd.Timedelta(seconds=286.5)


def test_session_derives_track_status(laps: Laps) -> None:
    session = ep.get_session(2024, "WEC", "Le Mans", "Race")
    session._laps = laps  # injected until Session.load is implemented (2.5)
    ts = session.track_status
    assert list(ts["Status"]) == ["GreenFlag", "FullCourseYellow", "GreenFlag"]
