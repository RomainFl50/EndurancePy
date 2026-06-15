"""Tests for the two-stage on-disk cache (offline-only)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from endurancepy.cache import Cache


def test_enable_cache_missing_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        Cache.enable_cache(tmp_path / "does-not-exist")


def test_enable_cache_and_info(tmp_path: Path) -> None:
    assert Cache.get_cache_info() == (None, None)
    Cache.enable_cache(tmp_path)
    path, size = Cache.get_cache_info()
    assert path == tmp_path
    assert isinstance(size, int)


def test_dataframe_roundtrip(tmp_path: Path) -> None:
    Cache.enable_cache(tmp_path)
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    Cache.save_dataframe("wec/2024/laps", df)
    loaded = Cache.load_dataframe("wec/2024/laps")
    assert loaded is not None
    pd.testing.assert_frame_equal(loaded, df)


def test_load_missing_returns_none(tmp_path: Path) -> None:
    Cache.enable_cache(tmp_path)
    assert Cache.load_dataframe("nope") is None


def test_metadata_roundtrip(tmp_path: Path) -> None:
    Cache.enable_cache(tmp_path)
    Cache.save_metadata("wec/2024/meta", {"event": "Le Mans", "laps": 311})
    assert Cache.load_metadata("wec/2024/meta") == {"event": "Le Mans", "laps": 311}


def test_disabled_context_blocks_load(tmp_path: Path) -> None:
    Cache.enable_cache(tmp_path)
    Cache.save_dataframe("k", pd.DataFrame({"a": [1]}))
    with Cache.disabled():
        assert Cache.load_dataframe("k") is None
    assert Cache.load_dataframe("k") is not None


def test_clear_cache_removes_parsed(tmp_path: Path) -> None:
    Cache.enable_cache(tmp_path)
    Cache.save_dataframe("k", pd.DataFrame({"a": [1]}))
    Cache.clear_cache()
    assert Cache.load_dataframe("k") is None
