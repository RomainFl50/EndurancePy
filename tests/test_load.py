"""Tests for Session.load (from path/bytes/URL) and parsed-laps caching."""

from __future__ import annotations

from pathlib import Path

import pytest

import endurancepy as ep
from endurancepy.cache import Cache
from endurancepy.exceptions import SessionNotAvailableError

FIXTURE = Path(__file__).parent / "fixtures" / "analysis_sample.csv"


def _session() -> ep.core.Session:
    return ep.get_session(2024, "WEC", "Le Mans", "Race")


def test_load_from_path(tmp_path: Path) -> None:
    Cache.enable_cache(tmp_path)
    session = _session()
    session.load(source=FIXTURE)
    assert len(session.laps) == 11
    assert session.cars == ["8", "7", "83"]
    assert list(session.track_status["Status"]) == [
        "GreenFlag",
        "FullCourseYellow",
        "GreenFlag",
    ]


def test_load_from_bytes(tmp_path: Path) -> None:
    Cache.enable_cache(tmp_path)
    session = _session()
    session.load(source=FIXTURE.read_bytes())
    assert len(session.laps) == 11


def test_load_caches_and_reuses(tmp_path: Path) -> None:
    Cache.enable_cache(tmp_path)
    _session().load(source=FIXTURE)  # populates the cache

    reused = _session()
    reused.load()  # no source -> must come from the cache
    assert len(reused.laps) == 11
    assert reused.get_car("8")["Position"] == 1


def test_load_without_source_or_cache_raises(tmp_path: Path) -> None:
    Cache.enable_cache(tmp_path)
    with pytest.raises(SessionNotAvailableError):
        _session().load()


def test_load_from_url_uses_client_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    Cache.enable_cache(tmp_path)
    payload = FIXTURE.read_bytes()
    monkeypatch.setattr("endurancepy.alkamel.client.download", lambda url: payload)
    session = _session()
    session.load(source="https://example.test/23_Analysis_Race.CSV")
    assert len(session.laps) == 11
