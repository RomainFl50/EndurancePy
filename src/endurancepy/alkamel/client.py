"""HTTP client and URL construction for the Al Kamel results portals.

Verified file-URL template (see ``docs/analyse_fastf1.md`` §14.2)::

    https://<host>/Results/<NN_YYYY>/<NN_EVENT>/
        <NNN_SERIES>/<YYYYMMDDHHMM_SESSION>/[Hour N/]<FILE>

The same structure serves every Al Kamel championship; only the host differs.
"""

from __future__ import annotations

from urllib.parse import quote

from endurancepy.cache import Cache
from endurancepy.logger import LOGGER

#: Default request headers (identify the client honestly; be a good citizen).
DEFAULT_HEADERS = {
    "User-Agent": "EndurancePy (+https://github.com/RomainFl50/EndurancePy)"
}

#: Default per-request timeout, in seconds.
REQUEST_TIMEOUT = 30


def build_results_url(
    host: str,
    season: str,
    event: str,
    series_folder: str,
    session: str,
    filename: str,
    *,
    hour: int | str | None = None,
) -> str:
    """Build a download URL into a portal's ``Results`` tree.

    Parameters
    ----------
    host:
        Portal host, e.g. ``"fiawec.alkamelsystems.com"``.
    season, event, series_folder, session:
        Path components, e.g. ``"13_2024"``, ``"04_LE MANS"``, ``"267_FIA WEC"``,
        ``"201905041330_Race"``. Spaces are URL-encoded.
    filename:
        The file to fetch, e.g. ``"23_Analysis_Race.CSV"``.
    hour:
        For races, the hour sub-folder (e.g. ``6`` -> ``"Hour 6"``).
    """
    parts = ["Results", season, event, series_folder, session]
    if hour is not None:
        parts.append(f"Hour {hour}")
    parts.append(filename)
    encoded = "/".join(quote(part, safe="") for part in parts)
    return f"https://{host}/{encoded}"


def download(url: str) -> bytes:
    """Download a file's bytes, honouring the cache.

    Uses the session returned by :meth:`endurancepy.cache.Cache.requests_session`
    (cached unless caching is disabled).
    """
    LOGGER.debug("Downloading %s", url)
    session = Cache.requests_session()
    response = session.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.content
