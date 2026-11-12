"""Public JSON discovery with synthetic fixtures only, never live requests."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pytest

import endurancepy as ep
from endurancepy.alkamel import client, discovery, manifests
from endurancepy.exceptions import SessionNotAvailableError

_ROOT = "https://files.example.test"
_GALLERY = f"{_ROOT}/wec/manifests/results.json"
_SEASON = f"{_ROOT}/wec/manifests/season.json"
_PREFIX = "wec/results/15_2026/08_MONZA/689_FIA WEC/202611081300_Race"


def _portal(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> list[Any]:
    calls: list[Any] = []
    responses: dict[str, Any] = {
        manifests.SETTINGS_URL: {
            "requiresAuth": False,
            "sections": {"results": {"dataAccess": "free"}},
            "galleriesUrl": _GALLERY,
        },
        _GALLERY: {
            "type": "seasons_index",
            "seasons": [
                {
                    "id": "15_2026",
                    "name": "2026",
                    "manifestUrl": "wec/manifests/season.json",
                },
                {"id": "zz_test"},
            ],
        },
        _SEASON: {
            "folders": [
                {
                    "children": [
                        {
                            "children": [
                                {"url": f"{_PREFIX}/06_Hour 6/23_Analysis_Race.CSV"}
                            ]
                        },
                        {"url": f"{_PREFIX}/01_Hour 1/03_Classification_Race.CSV"},
                        {"url": f"{_PREFIX}/06_Hour 6/03_Classification_Race.CSV"},
                        {"url": f"{_PREFIX}/06_Hour 6/26_Weather_Race.CSV"},
                        {"url": f"{_PREFIX}/06_Hour 6/23_Analysis_Race.PDF"},
                        {
                            "url": (
                                "wec/results/15_2026/08_MONZA/"
                                "00_Event Info/Timetable.pdf"
                            )
                        },
                    ]
                }
            ]
        },
        **overrides,
    }

    def fake_json(url: str, *, payload: object = None) -> dict[str, Any]:
        calls.append((url, payload))
        assert url in responses, f"Unexpected request: {url}"
        return responses[url]  # type: ignore[no-any-return]

    monkeypatch.setattr(client, "download_json", fake_json)
    return calls


def test_public_seasons_and_hour_race(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _portal(monkeypatch)
    assert discovery.fetch_seasons("fiawec.alkamelsystems.com") == ["15_2026"]
    assert calls[0] == (manifests.SETTINGS_URL, {"url": "fiawec.alkamelcloud.com"})
    records = discovery.fetch_index("fiawec.alkamelcloud.com", "15_2026")
    assert len(records) == 4
    files = discovery.resolve_session_files(
        records, event="Monza", session="Race", series_keyword="WEC"
    )
    analysis = files["analysis"]
    assert (
        analysis.season,
        analysis.event,
        analysis.series,
        analysis.session,
        analysis.hour,
    ) == ("15_2026", "08_MONZA", "689_FIA WEC", "202611081300_Race", 6)
    assert (
        analysis.url("unused.example.test")
        == f"{_ROOT}/{_PREFIX.replace(' ', '%20')}/06_Hour%206/23_Analysis_Race.CSV"
    )
    assert analysis.download_url == analysis.url("unused.example.test")
    assert files["classification"].hour == 6
    assert (
        discovery.fetch_index("fiawec.alkamelcloud.com", "15_2026", event="01_OTHER")
        == []
    )
    sessions = discovery.fetch_event_sessions(
        "fiawec.alkamelcloud.com", "15_2026", "08_MONZA", series_keyword="WEC"
    )
    assert sessions[0].duration == dt.timedelta(hours=6)


def test_series_index_and_absolute_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    _portal(
        monkeypatch,
        **{
            _GALLERY: {
                "type": "series_index",
                "series": [{"indexUrl": "wec/seasons.json"}],
            },
            f"{_ROOT}/wec/seasons.json": {
                "type": "seasons_index",
                "seasons": [{"id": "15_2026", "manifestUrl": _SEASON}],
            },
        },
    )
    assert len(discovery.fetch_index("elms.alkamelcloud.com", "15_2026")) == 4


def test_last_hour_is_numeric_and_order_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _portal(
        monkeypatch,
        **{
            _SEASON: {
                "folders": [
                    {
                        "children": [
                            {"url": f"{_PREFIX}/24_Hour 24/23_Analysis_Race.CSV"},
                            {"url": f"{_PREFIX}/24_Hour 24/03_Classification_Race.CSV"},
                            {"url": f"{_PREFIX}/09_Hour 9/03_Classification_Race.CSV"},
                        ]
                    }
                ]
            },
        },
    )
    records = discovery.fetch_index("fiawec.alkamelcloud.com", "15_2026")
    files = discovery.resolve_session_files(
        records, event="Monza", session="Race", series_keyword="WEC"
    )
    assert files["analysis"].hour == files["classification"].hour == 24


@pytest.mark.parametrize(
    "settings",
    [
        {"requiresAuth": True, "sections": {"results": {"dataAccess": "free"}}},
        {"requiresAuth": False, "sections": {"results": {"dataAccess": "registered"}}},
        {"sections": {"results": {"dataAccess": "free"}}},
        {},
    ],
)
def test_restricted_config_stops_before_gallery(
    monkeypatch: pytest.MonkeyPatch, settings: dict[str, Any]
) -> None:
    calls = _portal(monkeypatch, **{manifests.SETTINGS_URL: settings})
    with pytest.raises(SessionNotAvailableError, match="authentication"):
        discovery.fetch_seasons("fiawec.alkamelcloud.com")
    assert len(calls) == 1


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"type": "seasons_index", "seasons": None},
        {"type": "seasons_index", "seasons": [None]},
    ],
)
def test_invalid_index(monkeypatch: pytest.MonkeyPatch, value: dict[str, Any]) -> None:
    _portal(monkeypatch, **{_GALLERY: value})
    with pytest.raises(SessionNotAvailableError):
        discovery.fetch_seasons("fiawec.alkamelcloud.com")


def test_missing_season_and_invalid_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _portal(monkeypatch, **{_SEASON: {"folders": [{"children": "bad"}]}})
    with pytest.raises(SessionNotAvailableError, match="not listed"):
        discovery.fetch_index("fiawec.alkamelcloud.com", "99_2099")
    assert all(url != _SEASON for url, _ in calls)
    with pytest.raises(SessionNotAvailableError, match="children"):
        discovery.fetch_index("fiawec.alkamelcloud.com", "15_2026")


def test_absolute_url_encoding_and_credentials() -> None:
    url = f"{_ROOT}/wec/results/15_2026/08_MONZA/689_FIA%20WEC/file%20name.CSV"
    assert manifests.public_url(url) == url
    for unsafe in [
        "http://example.test/data.json",
        "https://user:pass@example.test/data",
        "",
    ]:
        with pytest.raises(SessionNotAvailableError):
            manifests.public_url(unsafe)


def test_public_load_without_explicit_season(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _portal(monkeypatch)
    analysis = (Path(__file__).parent / "fixtures/analysis_sample.csv").read_bytes()
    monkeypatch.setattr(client, "download", lambda url: analysis)
    ep.Cache.enable_cache(tmp_path)
    session = ep.get_session(2026, series="WEC", event="Monza", session="Race")
    session.load(weather=False)
    assert not session.laps.empty
    assert ep.get_event_schedule(2026, series="WEC").season == "15_2026"
