"""On-disk cache, mirroring :class:`fastf1.Cache`.

Two stages (see ``docs/plan_implementation.md`` §8):

1. **Raw HTTP responses**, via ``requests-cache`` (SQLite).
2. **Parsed data objects**, serialised as Parquet (+ JSON session metadata),
   namespaced by :data:`PARSER_VERSION` so a schema change invalidates them.

All methods are class methods (like FastF1). Caching is enabled by default; the
cache directory is resolved from :meth:`enable_cache`, then the
``ENDURANCEPY_CACHE`` environment variable, then an OS-default location.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import requests_cache

from endurancepy.logger import LOGGER

#: Environment variable used to locate the cache when not set explicitly.
CACHE_ENV_VAR = "ENDURANCEPY_CACHE"

#: Bumped whenever the parsed-data schema changes, to invalidate stage-2 files.
PARSER_VERSION = 1

_HTTP_CACHE_NAME = "endurancepy_http_cache"
_PARSED_SUBDIR = "parsed"
_HTTP_EXPIRE_SECONDS = 12 * 3600


def _default_cache_dir() -> Path:
    """Return the cache directory from the env var, else the OS default."""
    if env := os.environ.get(CACHE_ENV_VAR):
        return Path(env).expanduser()
    return Path.home() / ".cache" / "endurancepy"


class Cache:
    """Manage the on-disk cache. All methods are class methods (like FastF1)."""

    _cache_dir: Path | None = None
    _enabled: bool = True
    _offline: bool = False
    _http_session: Any = None  # lazily-built requests_cache.CachedSession

    # -- configuration ------------------------------------------------------
    @classmethod
    def enable_cache(cls, cache_dir: str | os.PathLike[str]) -> None:
        """Enable the cache, storing data under ``cache_dir`` (must exist)."""
        path = Path(cache_dir).expanduser()
        if not path.is_dir():
            raise NotADirectoryError(f"Cache directory does not exist: {path}")
        cls._cache_dir = path
        cls._enabled = True
        cls._http_session = None  # rebuild against the new directory
        LOGGER.debug("Cache enabled at %s", path)

    @classmethod
    def _resolve_dir(cls) -> Path:
        """Return the active cache directory, creating it if necessary."""
        path = cls._cache_dir or _default_cache_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_cache_info(cls) -> tuple[Path | None, int | None]:
        """Return ``(path, size_in_bytes)``, or ``(None, None)`` if unconfigured."""
        if cls._cache_dir is None:
            return (None, None)
        size = sum(f.stat().st_size for f in cls._cache_dir.rglob("*") if f.is_file())
        return (cls._cache_dir, size)

    @classmethod
    def clear_cache(
        cls, cache_dir: str | os.PathLike[str] | None = None, deep: bool = False
    ) -> None:
        """Delete cached data.

        Removes the parsed (stage-2) data. With ``deep=True``, also removes the
        raw HTTP (stage-1) SQLite cache.
        """
        path = (
            Path(cache_dir).expanduser()
            if cache_dir is not None
            else (cls._cache_dir or _default_cache_dir())
        )
        if not path.is_dir():
            raise NotADirectoryError(f"Cache directory does not exist: {path}")
        parsed = path / _PARSED_SUBDIR
        if parsed.is_dir():
            shutil.rmtree(parsed)
        if deep:
            for db in path.glob(_HTTP_CACHE_NAME + "*"):
                db.unlink()
            cls._http_session = None

    # -- enable/disable -----------------------------------------------------
    @classmethod
    def set_disabled(cls) -> None:
        """Disable caching while keeping the configured directory."""
        cls._enabled = False

    @classmethod
    def set_enabled(cls) -> None:
        """Re-enable caching after :meth:`set_disabled`."""
        cls._enabled = True

    @classmethod
    @contextmanager
    def disabled(cls) -> Iterator[None]:
        """Context manager that temporarily disables caching."""
        previous = cls._enabled
        cls._enabled = False
        try:
            yield
        finally:
            cls._enabled = previous

    @classmethod
    def offline_mode(cls, enabled: bool) -> None:
        """Only serve responses from the cache; do not make real requests."""
        cls._offline = enabled

    # -- stage 1: HTTP ------------------------------------------------------
    @classmethod
    def requests_session(cls) -> requests.Session:
        """Return a session: cached when enabled, plain otherwise."""
        if not cls._enabled:
            return requests.Session()
        if cls._http_session is None:
            db_path = cls._resolve_dir() / _HTTP_CACHE_NAME
            cls._http_session = requests_cache.CachedSession(
                cache_name=str(db_path),
                backend="sqlite",
                expire_after=_HTTP_EXPIRE_SECONDS,
                stale_if_error=True,
            )
        settings = getattr(cls._http_session, "settings", None)
        if settings is not None:
            settings.only_if_cached = cls._offline
        return cls._http_session

    # -- stage 2: parsed data ----------------------------------------------
    @classmethod
    def _parsed_dir(cls) -> Path:
        path = cls._resolve_dir() / _PARSED_SUBDIR / f"v{PARSER_VERSION}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def save_dataframe(cls, key: str, df: pd.DataFrame) -> Path:
        """Persist a parsed ``DataFrame`` under ``key`` (as Parquet)."""
        path = cls._parsed_dir() / f"{key}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)
        return path

    @classmethod
    def load_dataframe(cls, key: str) -> pd.DataFrame | None:
        """Load a parsed ``DataFrame`` for ``key``, or ``None`` if absent/disabled."""
        if not cls._enabled:
            return None
        path = cls._parsed_dir() / f"{key}.parquet"
        if not path.is_file():
            return None
        return pd.read_parquet(path)

    @classmethod
    def save_metadata(cls, key: str, metadata: dict[str, Any]) -> Path:
        """Persist a small JSON metadata blob under ``key``."""
        path = cls._parsed_dir() / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(metadata), encoding="utf-8")
        return path

    @classmethod
    def load_metadata(cls, key: str) -> dict[str, Any] | None:
        """Load a JSON metadata blob for ``key``, or ``None`` if absent/disabled."""
        if not cls._enabled:
            return None
        path = cls._parsed_dir() / f"{key}.json"
        if not path.is_file():
            return None
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
