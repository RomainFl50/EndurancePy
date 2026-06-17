# Examples

Runnable examples covering the whole package. **All examples load a real session
over the network** via auto-discovery (`Session.load(season=...)`) — no CSV path,
no bundled data. Just run them.

| File | Shows |
|---|---|
| [`quickstart.py`](quickstart.py) | Load a session, results & fastest laps |
| [`quickstart.ipynb`](quickstart.ipynb) | A full guided tour as a Jupyter notebook (outputs cleared) |
| [`schedule_example.py`](schedule_example.py) | Browse a season calendar (`get_event_schedule`) and load an event |
| [`lap_analysis.py`](lap_analysis.py) | Every `pick_*` filter, stints, track status, classification |
| [`standings_example.py`](standings_example.py) | `compute_standings` across rounds (overall, per class, custom points) |
| [`plot_pace_by_class.py`](plot_pace_by_class.py) | Box plot of green-flag pace per class |
| [`plot_lap_evolution.py`](plot_lap_evolution.py) | Lap-time evolution scatter, coloured by class |

## Running

```bash
pip install "endurancepy[plot]"     # plotting extra for the chart examples

python examples/quickstart.py
python examples/schedule_example.py
python examples/lap_analysis.py
python examples/standings_example.py
python examples/plot_pace_by_class.py
python examples/plot_lap_evolution.py
```

Each example uses a known season id (e.g. `08_2018-2019`); edit the
`get_session(...)` / `get_event_schedule(...)` calls to target another
series/season/event. The on-disk cache (`ep.Cache.enable_cache(...)`) means a
session is only downloaded and parsed once.

> Please respect the portals' terms of service; no Al Kamel data ships with the
> project. (CI runs these examples offline by faking the download layer.)
