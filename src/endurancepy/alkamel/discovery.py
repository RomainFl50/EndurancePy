"""Discovery of result files from an Al Kamel portal index page.

The portal's ``?season=<id>`` (and ``?season=<id>&evvent=<event>``) pages embed
the full list of downloadable files as ``Results/<season>/<event>/<series>/
<session>/[<hour>/]<file>`` paths. Parsing those paths gives a structured index
of every session's Analysis / Classification / Weather CSV (verified mechanism).

Listing the *seasons* themselves is not done here (the season selector is a JS
tree menu, not scrapeable from static HTML); callers provide the season id.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote, unquote

from rapidfuzz import fuzz

from endurancepy.exceptions import SessionNotAvailableError

_RESULTS_RE = re.compile(r"Results/[^\"'<>]+?\.CSV", re.IGNORECASE)
_HOUR_RE = re.compile(r"Hour\s*(\d+)", re.IGNORECASE)
_SESSION_PREFIX_RE = re.compile(r"^\d+_(.*)$")
_SESSION_TS_RE = re.compile(r"^(\d{12})_")
_EVENT_PREFIX_RE = re.compile(r"^(\d+)_(.*)$")
_SEASON_OPTION_RE = re.compile(r'value="(\d{2}_\d{4}(?:-\d{4})?)"')
_SEASON_TOKEN_RE = re.compile(r"\b\d{2}_\d{4}(?:-\d{4})?\b")
# Event folders are ``NN_NAME`` with an ALL-CAPS circuit name (e.g. ``07_LE
# MANS``). The upper-case-only character class excludes file/report prefixes
# (CamelCase, e.g. ``23_Analysis``) and the negative look-behind excludes
# 3-digit series folders (e.g. ``267_FIA WEC``); the look-ahead anchors the end
# to a tag/quote/slash boundary.
_EVENT_NAME_RE = re.compile(r"(?<!\d)(\d{2}_[A-Z0-9][A-Z0-9 .&'/\-]{2,50})(?=[\"'<>/])")


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


def fetch_seasons(host: str) -> list[str]:
    """Return the season ids (e.g. ``"13_2024"``) listed on a portal's home page.

    The season selector is a ``<select name="season">``; its option values are
    the ``NN_YYYY`` ids. Falls back to a page-wide token scan if needed.
    """
    from endurancepy.alkamel.client import download

    html = download(f"https://{host}/").decode("utf-8", "replace")
    ids = _SEASON_OPTION_RE.findall(html) or _SEASON_TOKEN_RE.findall(html)
    return sorted(dict.fromkeys(ids))


def parse_events(html: str) -> list[EventInfo]:
    """Extract the event folders (``NN_NAME``) from a season page's menu."""
    seen: dict[str, EventInfo] = {}
    for raw in _EVENT_NAME_RE.findall(html):
        folder = raw.strip()
        match = _EVENT_PREFIX_RE.match(folder)
        if not match:
            continue
        name = match.group(2).strip()
        if not name or re.fullmatch(r"\d{4}(?:-\d{4})?", name):
            continue  # season id, not an event
        if not re.search(r"[A-Z]", name):
            continue
        if folder not in seen:
            seen[folder] = EventInfo(
                round=int(match.group(1)),
                name=name,
                date=None,
                sessions=(),
                event_folder=folder,
            )
    return sorted(
        seen.values(), key=lambda e: (e.round if e.round is not None else 9999, e.name)
    )


def fetch_events(host: str, season: str) -> list[EventInfo]:
    """Download a season page and parse its full event list."""
    from endurancepy.alkamel.client import download

    html = download(f"https://{host}/?season={quote(season)}").decode(
        "utf-8", "replace"
    )
    return parse_events(html)


def fetch_event_sessions(
    host: str, season: str, event_folder: str, *, series_keyword: str | None = None
) -> list[str]:
    """List an event's session names, in chronological order.

    The season calendar only lists events (not their sessions); the sessions
    live on the event's own page (``?season=<id>&evvent=<folder>``). Fetches
    that page and returns the session labels (e.g. ``["Free Practice 1",
    "Qualifying", "Race"]``), ordered by their start timestamp.
    """
    records = fetch_index(host, season, event=event_folder)
    pool = records
    if series_keyword is not None:
        pool = [r for r in pool if series_keyword.lower() in r.series.lower()]
    folders = list(dict.fromkeys(r.session for r in pool))
    folders.sort(key=lambda f: session_datetime(f) or dt.datetime.min)
    return [_session_label(f) for f in folders]


def find_event(events: list[EventInfo], query: str) -> EventInfo:
    """Return the event best matching ``query`` (name or folder)."""
    if not events:
        raise SessionNotAvailableError("No events were discovered for this season.")
    options: dict[str, EventInfo] = {}
    for event in events:
        options[event.name] = event
        options[event.event_folder] = event
    return options[_best_match(query, list(options))]


def session_datetime(session_folder: str) -> dt.datetime | None:
    """Parse the ``YYYYMMDDHHMM`` timestamp prefix of a session folder."""
    match = _SESSION_TS_RE.match(session_folder)
    if not match:
        return None
    try:
        return dt.datetime.strptime(match.group(1), "%Y%m%d%H%M")
    except ValueError:
        return None


@dataclass(frozen=True)
class EventInfo:
    """A single event (meeting) derived from the discovered result files."""

    round: int | None
    name: str
    date: dt.datetime | None
    sessions: tuple[str, ...]
    event_folder: str


def build_events(
    records: list[ResultFile], *, series_keyword: str | None = None
) -> list[EventInfo]:
    """Group discovered records into events, ordered by round number."""
    pool = records
    if series_keyword is not None:
        pool = [r for r in pool if series_keyword.lower() in r.series.lower()]

    by_event: dict[str, list[ResultFile]] = {}
    for record in pool:
        by_event.setdefault(record.event, []).append(record)

    events = []
    for event_folder, recs in by_event.items():
        match = _EVENT_PREFIX_RE.match(event_folder)
        round_number = int(match.group(1)) if match else None
        name = match.group(2) if match else event_folder
        sessions = tuple(dict.fromkeys(_session_label(r.session) for r in recs))
        dates = [d for d in (session_datetime(r.session) for r in recs) if d]
        events.append(
            EventInfo(
                round=round_number,
                name=name,
                date=max(dates) if dates else None,
                sessions=sessions,
                event_folder=event_folder,
            )
        )
    events.sort(key=lambda e: (e.round if e.round is not None else 9999, e.name))
    return events
