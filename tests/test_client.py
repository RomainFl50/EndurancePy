"""Tests for the Al Kamel client (URL building + download, offline-only)."""

from __future__ import annotations

import pytest

from endurancepy.alkamel.client import (
    DEFAULT_HEADERS,
    REQUEST_TIMEOUT,
    build_results_url,
    download,
)
from endurancepy.cache import Cache


def test_build_results_url_basic() -> None:
    url = build_results_url(
        "fiawec.alkamelsystems.com",
        "13_2024",
        "01_LOSAIL",
        "581_FR Middle East Championship",
        "202502261915_Free Practice",
        "23_Analysis_Free Practice.CSV",
    )
    assert url == (
        "https://fiawec.alkamelsystems.com/Results/13_2024/01_LOSAIL/"
        "581_FR%20Middle%20East%20Championship/202502261915_Free%20Practice/"
        "23_Analysis_Free%20Practice.CSV"
    )


def test_build_results_url_with_hour() -> None:
    url = build_results_url(
        "fiawec.alkamelsystems.com",
        "08_2018-2019",
        "07_SPA FRANCORCHAMPS",
        "267_FIA WEC",
        "201905041330_Race",
        "23_Analysis_Race_Hour 6.CSV",
        hour=6,
    )
    assert url == (
        "https://fiawec.alkamelsystems.com/Results/08_2018-2019/"
        "07_SPA%20FRANCORCHAMPS/267_FIA%20WEC/201905041330_Race/Hour%206/"
        "23_Analysis_Race_Hour%206.CSV"
    )


def test_download_uses_cache_session(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class _FakeResponse:
        content = b"payload"

        def raise_for_status(self) -> None:
            captured["raised"] = True

    class _FakeSession:
        def get(
            self, url: str, headers: object = None, timeout: object = None
        ) -> object:
            captured["url"] = url
            captured["headers"] = headers
            captured["timeout"] = timeout
            return _FakeResponse()

    monkeypatch.setattr(
        Cache, "requests_session", classmethod(lambda cls: _FakeSession())
    )

    assert download("https://example.test/file.CSV") == b"payload"
    assert captured["url"] == "https://example.test/file.CSV"
    assert captured["headers"] == DEFAULT_HEADERS
    assert captured["timeout"] == REQUEST_TIMEOUT
    assert captured["raised"] is True
