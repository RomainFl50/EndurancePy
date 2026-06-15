"""HTTP client and URL construction for the Al Kamel results portals.

Verified file-URL template (see ``docs/analyse_fastf1.md`` §14.2)::

    https://<host>/Results/<NN_YYYY>/<NN_EVENT>/
        <NNN_SERIES>/<YYYYMMDDHHMM_SESSION>/[Hour N/]<FILE>

Implementation lands in milestone 2.1.
"""

from __future__ import annotations

#: Default request headers (identify the client honestly; be a good citizen).
DEFAULT_HEADERS = {
    "User-Agent": "EndurancePy (+https://github.com/RomainFl50/EndurancePy)"
}


def build_results_url(host: str, *path_parts: str) -> str:
    """Build a URL into a portal's ``Results`` tree from path components."""
    raise NotImplementedError


def download(url: str) -> bytes:
    """Download a file, honouring the cache. Not implemented yet (milestone 2.1)."""
    raise NotImplementedError
