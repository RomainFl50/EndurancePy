"""EndurancePy — endurance racing timing & results data in Python.

Inspired by `FastF1 <https://github.com/theOehrly/Fast-F1>`_, EndurancePy aims to
provide the same kind of convenient, pandas-based access to timing and results
data, but for endurance racing series (WEC, ELMS, Asian Le Mans Series, Le Mans
Cup, IMSA), built on top of the publicly available Al Kamel Systems archives.

This package is in an early stage: the public API surface below is defined, but
most data-loading functionality is not implemented yet (it raises
``NotImplementedError``). See the project README and roadmap for status.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from endurancepy.cache import Cache
from endurancepy.events import (
    Event,
    EventSchedule,
    Series,
    get_event,
    get_event_schedule,
    get_session,
)
from endurancepy.logger import set_log_level

try:
    __version__ = version("endurancepy")
except PackageNotFoundError:  # pragma: no cover - not installed (e.g. source tree)
    __version__ = "0.0.0"

__all__ = [
    "Cache",
    "Event",
    "EventSchedule",
    "Series",
    "__version__",
    "get_event",
    "get_event_schedule",
    "get_session",
    "set_log_level",
]
