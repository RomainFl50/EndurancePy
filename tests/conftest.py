"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from endurancepy.cache import Cache


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
