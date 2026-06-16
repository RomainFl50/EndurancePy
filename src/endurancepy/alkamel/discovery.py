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
from dataclasses import dataclass
from urllib.parse import quote

_RESULTS_RE = re.compile(r"Results/[^\"'<>]+?\.CSV", re.IGNORECASE)
_HOUR_RE = re.compile(r"Hour\s*(\d+)", re.IGNORECASE)


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
