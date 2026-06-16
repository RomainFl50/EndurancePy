# Examples

Runnable examples covering the whole package.

| File | Network? | Shows |
|---|---|---|
| [`quickstart.py`](quickstart.py) | **Yes** | Load a real session via `Session.load(season=...)`, results & fastest laps. |
| [`quickstart.ipynb`](quickstart.ipynb) | **Yes** | A full guided tour as a Jupyter notebook (outputs cleared). |
| [`schedule_example.py`](schedule_example.py) | **Yes** | Browse a season calendar (`get_event_schedule`) and load an event. |
| [`lap_analysis.py`](lap_analysis.py) | No | Parse a **local** Analysis CSV: every `pick_*` filter, stints, track status, classification. |
| [`standings_example.py`](standings_example.py) | No | Championship `compute_standings` (overall, per class, custom points). |
| [`plot_pace_by_class.py`](plot_pace_by_class.py) | No | Box plot of green-flag pace per class. |
| [`plot_lap_evolution.py`](plot_lap_evolution.py) | No | Lap-time evolution scatter, coloured by class. |

## Running

```bash
pip install "endurancepy[plot]"          # plotting extra for the chart examples

# network (auto-discovery from the portal)
python examples/quickstart.py
python examples/schedule_example.py

# offline (give it a CSV you downloaded yourself)
python examples/lap_analysis.py        path/to/23_Analysis_Race.CSV
python examples/standings_example.py   path/to/23_Analysis_Race.CSV
python examples/plot_pace_by_class.py  path/to/23_Analysis_Race.CSV out.png
python examples/plot_lap_evolution.py  path/to/23_Analysis_Race.CSV evo.png
```

**No Al Kamel data is bundled** — the offline examples take a CSV path you
provide; please respect the portals' terms of service. Enable the cache once
with `ep.Cache.enable_cache("./cache")` so sessions download/parse only once.
