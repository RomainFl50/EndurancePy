"""Smoke tests: the package imports and its public API/skeleton is wired up."""

from __future__ import annotations

import pytest

import endurancepy as ep
from endurancepy import Series
from endurancepy.exceptions import SeriesNotSupportedError


def test_version_is_a_string() -> None:
    assert isinstance(ep.__version__, str)


@pytest.mark.parametrize(
    "name",
    [
        "get_session",
        "get_event",
        "get_event_schedule",
        "Cache",
        "Series",
        "Event",
        "EventSchedule",
        "set_log_level",
    ],
)
def test_public_api_is_exported(name: str) -> None:
    assert hasattr(ep, name)


def test_series_coerce_and_host() -> None:
    assert Series.coerce("wec") is Series.WEC
    assert Series.coerce(Series.IMSA) is Series.IMSA
    assert Series.WEC.host == "fiawec.alkamelsystems.com"


def test_get_session_builds_unloaded_object() -> None:
    session = ep.get_session(2024, "WEC", "Le Mans", "Race")
    assert session.year == 2024
    assert session.series is Series.WEC
    assert session.event == "Le Mans"
    assert session.name == "Race"


def test_unsupported_series_raises() -> None:
    with pytest.raises(SeriesNotSupportedError):
        ep.get_session(2024, "F1", "Monza", "Race")
