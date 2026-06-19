"""Interactive stint/strategy chart for a real session (loaded over the network).

Requires the interactive extra (``pip install endurancepy[interactive]``). Run::

    python examples/plot_strategy.py

Writes a standalone, interactive HTML chart: one bar per stint, per car,
coloured by class. Zoom into a window, hover for the driver and lap range, click
the legend to isolate a class. No CSV path needed.
"""

from __future__ import annotations

from pathlib import Path

import endurancepy as ep
from endurancepy import plotting
from endurancepy.core import Session


def plot(session: Session, output: str | Path = "strategy.html") -> Path:
    """Render the stint/strategy chart for a loaded session to an HTML file."""
    fig = plotting.plot_strategy(session, title="Race strategy by car")
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
