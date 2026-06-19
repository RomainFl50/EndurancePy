"""Interactive race trace (with neutralisations) for a real session.

Requires the interactive extra (``pip install endurancepy[interactive]``). Run::

    python examples/plot_race_trace.py

Writes a standalone, interactive HTML "race trace": each car's cumulative delta
to a constant reference pace, with the full-course-yellow / safety-car windows
shaded. Rising = gaining on the reference pace, falling = losing.
"""

from __future__ import annotations

from pathlib import Path

import endurancepy as ep
from endurancepy import plotting
from endurancepy.core import Session


def plot(session: Session, output: str | Path = "race_trace.html") -> Path:
    """Render the race trace (with track-status overlay) to an HTML file."""
    fig = plotting.plot_race_trace(session)
    plotting.add_track_status(fig, session)  # shade FCY / SC / red-flag windows
    output = Path(output)
    fig.write_html(output)
    return output


def main() -> None:
    ep.set_log_level("INFO")  # show discovery/download progress on stderr
    Path("./endurancepy-cache").mkdir(exist_ok=True)
    ep.Cache.enable_cache("./endurancepy-cache")
    session = ep.get_session(2019, "WEC", "Spa", "Race")
    session.load(season="08_2018-2019")
    print("Saved", plot(session))


if __name__ == "__main__":
    main()
