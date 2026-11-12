"""Public Al Kamel settings and JSON document trees; no authentication flows."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from endurancepy.alkamel import client
from endurancepy.exceptions import SessionNotAvailableError

if TYPE_CHECKING:
    from endurancepy.alkamel.discovery import ResultFile

SETTINGS_URL = "https://5ucg0oksmg.execute-api.us-west-2.amazonaws.com/dev/v2/settings"
_SEASON_ID = re.compile(r"^\d+_\d{4}(?:-\d{4})?$")


def public_url(path: str, origin: str = "") -> str:
    """Resolve relative paths from the gallery origin and encode exactly once."""
    if not isinstance(path, str) or not path:
        raise SessionNotAvailableError("Al Kamel manifest is missing a URL.")
    url = urlsplit(urljoin(origin + "/", path))
    if (
        url.scheme != "https"
        or not url.netloc
        or url.username is not None
        or url.password is not None
    ):
        raise SessionNotAvailableError("Al Kamel requires a public HTTPS URL.")
    encoded = "/".join(quote(unquote(part), safe="") for part in url.path.split("/"))
    return urlunsplit((url.scheme, url.netloc, encoded, url.query, url.fragment))


def _items(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key)
    if not isinstance(value, list) or any(not isinstance(v, dict) for v in value):
        raise SessionNotAvailableError(f"Al Kamel invalid manifest field: {key}")
    return value


def season_index(host: str) -> tuple[str, dict[str, str]]:
    """Return gallery origin and season-id -> manifest URL (preserve NN_YYYY)."""
    domain = (
        host.removesuffix(".alkamelsystems.com") + ".alkamelcloud.com"
        if host.endswith(".alkamelsystems.com")
        else host
    )
    settings = client.download_json(SETTINGS_URL, payload={"url": domain})
    sections = settings.get("sections")
    results = sections.get("results") if isinstance(sections, dict) else None
    access = results.get("dataAccess") if isinstance(results, dict) else None
    if settings.get("requiresAuth") is not False or access != "free":
        raise SessionNotAvailableError(
            "Al Kamel data requires authentication or restricted access; stopping."
        )
    gallery = public_url(settings.get("galleriesUrl", ""))
    parsed = urlsplit(gallery)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    index = client.download_json(gallery)
    indexes = [index]
    if index.get("type") == "series_index":
        indexes = [
            client.download_json(public_url(series.get("indexUrl", ""), origin))
            for series in _items(index, "series")
        ]
    seasons: dict[str, str] = {}
    for item in indexes:
        if item.get("type") != "seasons_index":
            raise SessionNotAvailableError("Al Kamel invalid seasons index.")
        for season in _items(item, "seasons"):
            sid = season.get("id")
            if not isinstance(sid, str) or not _SEASON_ID.fullmatch(sid):
                continue  # e.g. ELMS's advertised zz_test is not a season
            url = public_url(season.get("manifestUrl", ""), origin)
            if sid in seasons and seasons[sid] != url:
                raise SessionNotAvailableError(f"Al Kamel ambiguous season: {sid}")
            seasons[sid] = url
    return origin, seasons


def document_urls(nodes: list[dict[str, Any]], origin: str) -> Iterator[str]:
    """Walk all depths, including race Hour N folders."""
    for node in nodes:
        if node.get("url"):
            yield public_url(node["url"], origin)
        if "children" in node:
            yield from document_urls(_items(node, "children"), origin)


def result_files(host: str, season: str) -> list[ResultFile]:
    """Load only the requested season's advertised manifest and CSV leaves."""
    from endurancepy.alkamel.discovery import _parse_path

    origin, seasons = season_index(host)
    if season not in seasons:
        raise SessionNotAvailableError(f"Al Kamel season not listed: {season}")
    manifest = client.download_json(seasons[season])
    records = []
    seen = set()
    for url in document_urls(_items(manifest, "folders"), origin):
        if not urlsplit(url).path.lower().endswith(".csv") or url in seen:
            continue
        seen.add(url)
        record = _parse_path(urlsplit(url).path.lstrip("/"), download_url=url)
        if record is not None and record.season == season:
            records.append(record)
    return records
