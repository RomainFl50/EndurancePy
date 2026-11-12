"""Anonymous, cache-aware HTTP and legacy URL construction for Al Kamel."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlsplit

import requests

from endurancepy.cache import Cache
from endurancepy.exceptions import SessionNotAvailableError
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


def _request(url: str, *, payload: dict[str, str] | None = None) -> requests.Response:
    """Stop on HTTP errors/redirects; never acquire or send authentication."""
    parsed = urlsplit(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise SessionNotAvailableError("Expected a public HTTP(S) URL.")
    session = Cache.requests_session()
    # No implicit .netrc credentials, persisted cookies or session auth/headers.
    session.trust_env = False
    session.auth = None
    session.cookies.clear()
    session.headers.clear()
    try:
        response = session.request(
            "GET" if payload is None else "POST",
            url,
            json=payload,
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        if 300 <= response.status_code < 400:
            raise SessionNotAvailableError("Al Kamel redirected the request; stopping.")
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SessionNotAvailableError(
            f"Al Kamel request failed for {url}: {exc}"
        ) from exc
    return response


def download_json(url: str, *, payload: dict[str, str] | None = None) -> dict[str, Any]:
    """GET a public manifest or POST settings, through the HTTP cache."""
    response = _request(url, payload=payload)
    try:
        data = response.json()
    except ValueError as exc:
        raise SessionNotAvailableError(
            f"Al Kamel returned invalid JSON: {url}"
        ) from exc
    if not isinstance(data, dict):
        raise SessionNotAvailableError(f"Al Kamel expected a JSON object: {url}")
    return data


def download(url: str) -> bytes:
    """Download a file's bytes, honouring the cache.

    Uses the session returned by :meth:`endurancepy.cache.Cache.requests_session`
    (cached unless caching is disabled).
    """
    LOGGER.debug("Downloading %s", url)
    response = _request(url)
    from_cache = getattr(response, "from_cache", False)
    LOGGER.info(
        "%s %s (%d bytes)",
        "CACHE" if from_cache else "GET",
        url,
        len(response.content),
    )
    return response.content
