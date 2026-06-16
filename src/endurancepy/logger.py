"""Logging configuration for EndurancePy."""

from __future__ import annotations

import logging

LOGGER = logging.getLogger("endurancepy")
LOGGER.addHandler(logging.NullHandler())


def set_log_level(level: int | str) -> None:
    """Set the logging level for the ``endurancepy`` logger.

    Parameters
    ----------
    level:
        A standard :mod:`logging` level, either as an integer (e.g.
        :data:`logging.INFO`) or its name (e.g. ``"INFO"``).
    """
    LOGGER.setLevel(level)
