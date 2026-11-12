"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from endurancepy.cache import Cache


@pytest.fixture
def mock_manifests(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Install an anonymous JSON portal made exclusively from synthetic paths."""

    def install(paths: list[str], seasons: tuple[str, ...] = ("08_2018-2019",)) -> None:
        def fake_json(url: str, *, payload: object = None) -> dict[str, Any]:
            if payload is not None:
                return {
                    "requiresAuth": False,
                    "sections": {"results": {"dataAccess": "free"}},
                    "galleriesUrl": "https://example.test/results.json",
                }
            if url == "https://example.test/results.json":
                return {
                    "type": "seasons_index",
                    "seasons": [{"id": s, "manifestUrl": f"{s}.json"} for s in seasons],
                }
            assert url in {f"https://example.test/{s}.json" for s in seasons}
            return {"folders": [{"children": [{"url": p} for p in paths]}]}

        monkeypatch.setattr("endurancepy.alkamel.client.download_json", fake_json)

    return install


@pytest.fixture(autouse=True)
def _reset_cache_state() -> Iterator[None]:
    """Reset the global ``Cache`` state around every test."""
    saved = (
        Cache._cache_dir,
        Cache._enabled,
        Cache._offline,
        Cache._http_session,
    )
    Cache._cache_dir = None
    Cache._enabled = True
    Cache._offline = False
    Cache._http_session = None
    try:
        yield
    finally:
        (
            Cache._cache_dir,
            Cache._enabled,
            Cache._offline,
            Cache._http_session,
        ) = saved
