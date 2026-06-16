"""Plotting helpers, mirroring :mod:`fastf1.plotting`.

For endurance racing, colour helpers are organised by class / team / manufacturer
rather than by driver. Requires the optional ``plot`` extra (matplotlib).
Implementation lands in milestone 2.6.
"""

from __future__ import annotations

__all__ = ["get_class_color", "get_team_color", "setup_mpl"]


def setup_mpl() -> None:
    """Apply EndurancePy's default matplotlib styling. Not implemented yet."""
    raise NotImplementedError


def get_class_color(class_name: str) -> str:
    """Return the colour associated with a racing class. Not implemented yet."""
    raise NotImplementedError


def get_team_color(team_name: str) -> str:
    """Return the colour associated with a team. Not implemented yet."""
    raise NotImplementedError
