"""Tests for the Al Kamel Weather CSV parser (verified format)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import endurancepy as ep
from endurancepy._types import WEATHER_COLUMNS
from endurancepy.alkamel.weather import read_weather

FIXTURE = Path(__file__).parent / "fixtures" / "weather_sample.csv"


def test_session_loads_weather_from_source() -> None:
    session = ep.get_session(2024, "WEC", "Spa", "Race")
    session.load(laps=False, weather_source=FIXTURE)
    assert len(session.weather_data) == 3


def test_weather_columns_and_length() -> None:
    weather = read_weather(FIXTURE)
    assert list(weather.columns) == list(WEATHER_COLUMNS)
    assert len(weather) == 3


def test_time_is_relative_to_first_sample() -> None:
    weather = read_weather(FIXTURE)
    assert weather["Time"].iloc[0] == pd.Timedelta(0)
    assert weather["Time"].iloc[1] == pd.Timedelta(seconds=60)
    assert weather["Time"].iloc[2] == pd.Timedelta(seconds=120)


def test_channel_values() -> None:
    weather = read_weather(FIXTURE)
    assert round(weather["AirTemp"].iloc[0], 3) == 6.056
    assert weather["TrackTemp"].iloc[1] == 11
    assert weather["Humidity"].iloc[0] == 69
    assert weather["Pressure"].iloc[0] == 960.549
    assert weather["WindDirection"].iloc[2] == 180
    assert weather["Rainfall"].isna().all()  # not provided by Al Kamel
