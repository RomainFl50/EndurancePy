"""Discovery of result files from an Al Kamel portal index page.

The portal's ``?season=<id>`` (and ``?season=<id>&evvent=<event>``) pages embed
the full list of downloadable files as ``Results/<season>/<event>/<series>/
<session>/[<hour>/]<file>`` paths. Parsing those paths gives a structured index
of every session's Analysis / Classification / Weather CSV (verified mechanism).

Listing the *seasons* themselves is not done here (the season selector is a JS
tree menu, not scrapeable from static HTML); callers provide the season id.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote, unquote

from rapidfuzz import fuzz

from endurancepy.exceptions import SessionNotAvailableError

_RESULTS_RE = re.compile(r"Results/[^\"'<>]+?\.CSV", re.IGNORECASE)
_HOUR_RE = re.compile(r"Hour\s*(\d+)", re.IGNORECASE)
_SESSION_PREFIX_RE = re.compile(r"^\d+_(.*)$")


def _kind(filename: str) -> str:
    lower = filename.lower()
    if "analysis" in lower:
        return "analysis"
    if "classification" in lower:
        return "classification"
    if "weather" in lower:
        return "weather"
    return "other"


@dataclass(frozen=True)
class ResultFile:
    """A single downloadable result file discovered on the portal."""

    season: str
    event: str
    series: str
    session: str
    hour: int | None
    filename: str
    kind: str
    path: str

    def url(self, host: str) -> str:
        """Build the absolute download URL for a given portal host."""
        encoded = "/".join(quote(part, safe="") for part in self.path.split("/"))
        return f"https://{host}/{encoded}"


def parse_results_paths(html: str) -> list[str]:
    """Return the unique ``Results/...CSV`` paths found in a portal page."""
    return list(dict.fromkeys(_RESULTS_RE.findall(html)))


def _parse_path(path: str) -> ResultFile | None:
    # Portal hrefs are percent-encoded; decode so components are human-readable
    # (and so url() re-encodes exactly once).
    path = unquote(path)
    parts = path.split("/")
    # Results / season / event / series / session / [hour ...] / file
    if len(parts) < 6 or parts[0] != "Results":
        return None
    season, event, series, session = parts[1], parts[2], parts[3], parts[4]
    rest = parts[5:]
    filename = rest[-1]
    hour: int | None = None
    for segment in rest[:-1]:
        match = _HOUR_RE.search(segment)
        if match:
            hour = int(match.group(1))
    return ResultFile(
        season=season,
        event=event,
        series=series,
        session=session,
        hour=hour,
        filename=filename,
        kind=_kind(filename),
        path=path,
    )


def index_page(html: str) -> list[ResultFile]:
    """Parse a portal page into a list of :class:`ResultFile` records."""
    records = [_parse_path(p) for p in parse_results_paths(html)]
    return [r for r in records if r is not None]


def find_files(
    records: list[ResultFile],
    *,
    kind: str | None = None,
    event: str | None = None,
    session: str | None = None,
    hour: int | None = None,
) -> list[ResultFile]:
    """Filter discovered records by kind / event / session substrings and hour."""

    def matches(record: ResultFile) -> bool:
        if kind is not None and record.kind != kind:
            return False
        if event is not None and event.lower() not in record.event.lower():
            return False
        if session is not None and session.lower() not in record.session.lower():
            return False
        if hour is not None and record.hour != hour:
            return False
        return True

    return [record for record in records if matches(record)]


def _session_label(session_folder: str) -> str:
    """Strip the timestamp prefix from a session folder (``201905041330_Race``)."""
    match = _SESSION_PREFIX_RE.match(session_folder)
    return match.group(1) if match else session_folder


def _best_match(
    query: str,
    candidates: list[str],
    *,
    label: Callable[[str], str] = lambda c: c,
) -> str:
    """Best match for ``query`` among ``candidates``.

    Prefers case-insensitive substring containment (shortest matching label, the
    most specific), e.g. ``"Spa"`` -> ``"SPA FRANCORCHAMPS"``; otherwise falls
    back to ``partial_ratio`` (``WRatio`` does not discriminate short queries).
    """
    if not candidates:
        raise SessionNotAvailableError(f"No candidates to match {query!r} against.")
    needle = query.strip().lower()
    contains = [c for c in candidates if needle in label(c).lower()]
    if contains:
        return min(contains, key=lambda c: len(label(c)))
    return max(candidates, key=lambda c: fuzz.partial_ratio(needle, label(c).lower()))


def resolve_session_files(
    records: list[ResultFile],
    *,
    event: str,
    session: str,
    series_keyword: str | None = None,
) -> dict[str, ResultFile]:
    """Pick the Analysis/Classification/Weather file for the best-matching session.

    The event and session are fuzzy-matched against the discovered folder names.
    For multi-hour races, the latest hour is chosen for each file kind.
    """
    pool = records
    if series_keyword is not None:
        pool = [r for r in pool if series_keyword.lower() in r.series.lower()]
    if not pool:
        raise SessionNotAvailableError("No matching result files were discovered.")

    chosen_event = _best_match(event, list(dict.fromkeys(r.event for r in pool)))
    pool = [r for r in pool if r.event == chosen_event]

    chosen_session = _best_match(
        session,
        list(dict.fromkeys(r.session for r in pool)),
        label=_session_label,
    )
    pool = [r for r in pool if r.session == chosen_session]

    resolved: dict[str, ResultFile] = {}
    for kind in ("analysis", "classification", "weather"):
        matching = [r for r in pool if r.kind == kind]
        if matching:
            resolved[kind] = max(
                matching, key=lambda r: r.hour if r.hour is not None else -1
            )
    return resolved


def fetch_index(host: str, season: str, event: str | None = None) -> list[ResultFile]:
    """Download a portal ``?season=`` page and parse it into ResultFile records."""
    from endurancepy.alkamel.client import download

    url = f"https://{host}/?season={quote(season)}"
    if event is not None:
        url += f"&evvent={quote(event)}"
    html = download(url).decode("utf-8", "replace")
    return index_page(html)
