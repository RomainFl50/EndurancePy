"""On-disk cache, mirroring :class:`fastf1.Cache`.

Two stages are planned (see ``docs/plan_implementation.md`` §8):

1. Raw HTTP responses, via ``requests-cache`` (SQLite).
2. Parsed data objects, serialised as Parquet (+ JSON session metadata).

The public API surface is defined here; the implementation lands in milestone
2.1 and currently raises :class:`NotImplementedError`.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Environment variable used to locate the cache when not set explicitly.
CACHE_ENV_VAR = "ENDURANCEPY_CACHE"

#: Bumped whenever the parsed-data schema changes, to invalidate stage-2 files.
PARSER_VERSION = 1


def _default_cache_dir() -> Path:
    """Return the OS-appropriate default cache directory."""
    if (env := os.environ.get(CACHE_ENV_VAR)) is not None:
        return Path(env).expanduser()
    return Path.home() / ".cache" / "endurancepy"


class Cache:
    """Manage the on-disk cache. All methods are class methods (like FastF1)."""

    _cache_dir: Path | None = None
    _enabled: bool = True

    @classmethod
    def enable_cache(cls, cache_dir: str | os.PathLike[str]) -> None:
        """Enable the cache, storing data under ``cache_dir`` (must exist)."""
        path = Path(cache_dir).expanduser()
        if not path.is_dir():
            raise NotADirectoryError(f"Cache directory does not exist: {path}")
        cls._cache_dir = path
        cls._enabled = True

    @classmethod
    def clear_cache(cls, cache_dir: str | os.PathLike[str] | None = None) -> None:
        """Delete cached data. Not implemented yet (milestone 2.1)."""
        raise NotImplementedError

    @classmethod
    def get_cache_info(cls) -> tuple[Path | None, int | None]:
        """Return ``(path, size_in_bytes)`` or ``(None, None)`` if unconfigured."""
        return (cls._cache_dir, None)

    @classmethod
    def set_disabled(cls) -> None:
        """Disable caching while keeping the configured directory."""
        cls._enabled = False

    @classmethod
    def set_enabled(cls) -> None:
        """Re-enable caching after :meth:`set_disabled`."""
        cls._enabled = True
