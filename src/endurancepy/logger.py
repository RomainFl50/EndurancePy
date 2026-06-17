"""Logging configuration for EndurancePy.

The library logs under the ``endurancepy`` logger (with a :class:`NullHandler`
so it stays silent by default). Call :func:`set_log_level` to both raise the
level *and* attach a console handler, so loading/discovery progress is visible:

>>> import endurancepy as ep
>>> ep.set_log_level("INFO")   # now downloads, discovery, etc. print to stderr
"""

from __future__ import annotations

import logging
import sys

__all__ = ["LOGGER", "enable_console_logging", "set_log_level"]

LOGGER = logging.getLogger("endurancepy")
LOGGER.addHandler(logging.NullHandler())

_console_handler: logging.Handler | None = None


def enable_console_logging(level: int | str | None = None) -> None:
    """Attach a stderr handler to the ``endurancepy`` logger (idempotent).

    Parameters
    ----------
    level:
        Optional level for the handler (and the logger). If omitted, the
        logger's current level is left unchanged.
    """
    global _console_handler
    if _console_handler is None:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] endurancepy: %(message)s", "%H:%M:%S"
            )
        )
        LOGGER.addHandler(handler)
        _console_handler = handler
    if level is not None:
        LOGGER.setLevel(level)
        _console_handler.setLevel(level)


def set_log_level(level: int | str, *, console: bool = True) -> None:
    """Set the level of the ``endurancepy`` logger.

    Parameters
    ----------
    level:
        A standard :mod:`logging` level, as an integer (e.g.
        :data:`logging.INFO`) or its name (e.g. ``"INFO"``).
    console:
        When ``True`` (default), also attach a console (stderr) handler so the
        logs are actually shown. Set to ``False`` to only change the level and
        leave handler configuration to the application.
    """
    LOGGER.setLevel(level)
    if console:
        enable_console_logging(level)
