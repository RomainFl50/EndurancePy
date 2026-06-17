"""Tests for the formatting helpers."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from endurancepy.utils import format_laptime, format_timedelta


def test_format_lap_minutes() -> None:
    assert format_timedelta(pd.Timedelta("0 days 00:01:58.056")) == "1:58.056"


def test_format_with_hours() -> None:
    value = pd.Timedelta(hours=3, minutes=12, seconds=45, milliseconds=678)
    assert format_timedelta(value) == "3:12:45.678"


def test_format_without_millis() -> None:
    assert format_timedelta(pd.Timedelta(seconds=85), millis=False) == "1:25"


def test_format_accepts_plain_timedelta() -> None:
    assert format_timedelta(dt.timedelta(seconds=4, milliseconds=2)) == "0:04.002"


def test_format_missing_values_are_blank() -> None:
    assert format_timedelta(None) == ""
    assert format_timedelta(pd.NaT) == ""


def test_format_rounds_milliseconds() -> None:
    # 58.5599s rounds to the nearest millisecond -> 58.560.
    assert (
        format_timedelta(pd.Timedelta(seconds=58, microseconds=559_900)) == "0:58.560"
    )


def test_format_laptime_is_alias() -> None:
    assert format_laptime is format_timedelta
