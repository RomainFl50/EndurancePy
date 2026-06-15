"""Discovery of seasons, events and sessions from an Al Kamel portal index.

The navigation layer uses ``?season=<NN_YYYY>&evvent=<NN_EVENT>`` (note the
deliberate ``evvent`` spelling). Implementation lands in milestone 2.5.
"""

from __future__ import annotations


def list_seasons(host: str) -> list[str]:
    """List available season identifiers for a portal. Not implemented yet."""
    raise NotImplementedError


def list_events(host: str, season: str) -> list[str]:
    """List events of a season. Not implemented yet."""
    raise NotImplementedError


def list_sessions(host: str, season: str, event: str) -> list[str]:
    """List sessions of an event. Not implemented yet."""
    raise NotImplementedError
