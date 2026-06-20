"""Exception types raised across EndurancePy."""

from __future__ import annotations


class EndurancePyError(Exception):
    """Base class for all EndurancePy-specific exceptions."""


class DataNotLoadedError(EndurancePyError):
    """Raised when accessing session data before :meth:`Session.load` was called."""


class SessionNotAvailableError(EndurancePyError):
    """Raised when the requested session cannot be found or has no data."""


class SeriesNotSupportedError(EndurancePyError):
    """Raised when an unknown or unsupported racing series is requested."""


class RegulationsNotAvailableError(EndurancePyError):
    """Raised when no stored regulations exist for the requested series/season."""


class ParsingError(EndurancePyError):
    """Raised when a timing archive file cannot be parsed as expected."""
