# Examples

Runnable examples for EndurancePy.

| File | Network? | What it shows |
|---|---|---|
| [`quickstart.py`](quickstart.py) | **Yes** | Load a real session via `Session.load(season=...)` (auto-discovery), then results & fastest laps. |
| [`quickstart.ipynb`](quickstart.ipynb) | **Yes** | The same, as a Jupyter notebook (outputs cleared). |
| [`lap_analysis.py`](lap_analysis.py) | No | Parse a **local** Analysis CSV: `pick_*` filters, fastest per class, classification from laps. |
| [`plot_pace_by_class.py`](plot_pace_by_class.py) | No | Box plot of green-flag pace per class (needs the `plot` extra). |

## Running

```bash
pip install -e ".[plot]"          # plotting extra for the chart example

python examples/quickstart.py                                   # needs internet
python examples/lap_analysis.py     path/to/23_Analysis_Race.CSV
python examples/plot_pace_by_class.py path/to/23_Analysis_Race.CSV out.png
```

For the offline examples, download an `..._Analysis_....CSV` from a results
portal yourself (e.g. a WEC/ELMS/IMSA session). **No Al Kamel data is bundled**
with the project — please respect the portals' terms of service.

> Tip: enable the cache once with `ep.Cache.enable_cache("./cache")` so sessions
> are only downloaded and parsed once.
