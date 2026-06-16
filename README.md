<h1 align="center">EndurancePy</h1>

<p align="center">
  <b>Access endurance racing timing & results data in Python — the way
  <a href="https://github.com/theOehrly/Fast-F1">FastF1</a> does it for Formula 1.</b>
</p>

<p align="center">
  <a href="#status"><img alt="Status" src="https://img.shields.io/badge/status-design%20phase-orange"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
</p>

---

## What is EndurancePy?

**EndurancePy** is a Python package that aims to make endurance racing data as
easy to analyse as FastF1 made Formula 1 data. It loads and exposes **timing and
results data** — lap times, sector times, stints, pit stops, classifications,
positions (overall *and* per class), weather and flag/track status — as
convenient, **pandas-based** objects, primarily from the publicly available
**Al Kamel Systems** timing archives.

> **Inspired by [FastF1](https://github.com/theOehrly/Fast-F1).** EndurancePy
> deliberately mirrors FastF1's design and API surface (`get_session()`,
> `Session.load()`, `Session.laps`, `Session.results`, `pick_*` filters, an
> on-disk cache, a `plotting` helper module, …) so that anyone familiar with
> FastF1 feels at home. EndurancePy is an independent project and is **not**
> affiliated with FastF1, the FIA, the ACO, IMSA, Al Kamel Systems, or any
> championship.

## Target championships

| Series | Full name | Timing source |
|---|---|---|
| **WEC** | FIA World Endurance Championship | Al Kamel |
| **ELMS** | European Le Mans Series | Al Kamel |
| **AsLMS** | Asian Le Mans Series | Al Kamel |
| **LMC** | (Michelin) Le Mans Cup | Al Kamel |
| **IMSA** | IMSA SportsCar Championship | Al Kamel (`imsa.results.alkamelcloud.com`) |

> Good news for the implementation: **all of these series are timed by Al Kamel**,
> so a single parser can cover them all — only the base host and minor URL
> details differ.

## Status

> ⚠️ **Early / design phase — no runnable code yet.** Contributions are very
> welcome (see [Contributing](#contributing)).

The first goal is explicit: **offer the same content as FastF1 wherever the
underlying data exists.** Two structural limitations are known up front:
endurance racing has **no public car telemetry** (no speed/RPM/gear/throttle/
brake/GPS streams) and **no normalised historical database** equivalent to
Ergast — everything else (calendars, sessions, classifications, laps/sectors/
stints/pit data, weather, flags) is within reach from the public timing
archives.

## Usage

The API mirrors FastF1, with an added **series** axis (several championships
coexist). Today, a session loads from an Analysis CSV (path, bytes or URL);
automatic discovery of remote files is not implemented yet.

```python
import endurancepy as ep

ep.Cache.enable_cache("./endurancepy-cache")

# Load a session from an Analysis CSV
session = ep.get_session(2024, series="WEC", event="Le Mans", session="Race")
session.load(source="path/to/23_Analysis_Race.CSV")

# Classification (per car / per class)
session.results
session.results.pick_classes("HYPERCAR")
session.cars                  # car numbers in finishing order

# Laps
laps = session.laps
laps.pick_cars(["7", "8"])
laps.pick_classes("LMGT3")
laps.pick_drivers("Kamui KOBAYASHI")
fastest = laps.pick_fastest()

# Derived side data
session.track_status          # green / FCY / SC / code 60 / red
```

See the **[usage guide](docs/usage.md)** and runnable **[examples/](examples/)**
(scripts + a Jupyter notebook) for more.

## Roadmap

- [x] Inventory FastF1's full content and API surface
- [x] Map FastF1 features → endurance data availability (Al Kamel)
- [x] License & project groundwork
- [x] Al Kamel client + two-stage cache
- [x] `Analysis` CSV parser → `Laps` (+ `pick_*` filters)
- [x] `SessionResults` (per car & per class), derived from laps
- [x] Track-status timeline (flags / FCY / SC / code 60)
- [x] `Session.load` from a file/bytes/URL + parsed-laps caching
- [x] Weather CSV parser + result-file discovery (verified formats)
- [x] Race Classification CSV parser → `SessionResults`
- [x] Auto-discovery: `Session.load(season=...)` finds & downloads the files
- [x] `Event` / `EventSchedule` (season calendars from a season id)
- [x] `plotting` colour helpers (by class / manufacturer)
- [ ] Championship standings module
- [ ] Docs, tests, packaging & PyPI release

## How it relates to FastF1

| FastF1 | EndurancePy | Notes |
|---|---|---|
| `fastf1.get_session()` | `ep.get_session(..., series=...)` | + series axis |
| `Session.load()` | `Session.load()` | downloads & parses Al Kamel files |
| `Session.laps` (`Laps`) | `Session.laps` (`Laps`) | + `Class`, `CarNumber`, `Manufacturer`, `PositionInClass` |
| `Session.results` (`SessionResults`) | `Session.results` | per car/crew & per class |
| `Lap.get_telemetry()` (`Telemetry`) | — | **no public endurance telemetry** |
| `fastf1.Cache` | `ep.Cache` | on-disk cache (essential for 24h races) |
| `fastf1.plotting` | `ep.plotting` | colours by class/team/manufacturer |
| `fastf1.ergast` | `ep.standings` (later) | rebuilt from results |

## Contributing

EndurancePy is an open, community project and contributions are welcome —
whether it's code, documentation, test data, or simply reporting which series /
seasons you'd like to see supported.

Please read **[CONTRIBUTING.md](CONTRIBUTING.md)** to get started, and note that
all participation is governed by our
**[Code of Conduct](CODE_OF_CONDUCT.md)**.

A good first step is to open an issue describing what you'd like to work on.

## Data sources & legal note

EndurancePy is built around **publicly published** endurance timing archives
(Al Kamel Systems results portals; official championship sites such as
`fiawec.com`, `imsa.com`). It is an **unofficial, community project** for
analysis and research purposes.

- All championship names, logos and data remain the property of their respective
  owners (FIA, ACO, IMSA, the championships, and Al Kamel Systems).
- **Al Kamel Systems explicitly asserts ownership of its timing data** and warns
  against redistribution without consent. EndurancePy is therefore designed to
  **download and parse data for personal/research use only** — it does **not**
  bundle, ship, or republish any raw timing archives. Please do the same.
- Always respect the terms of service and `robots.txt` of any site you fetch
  from, and be considerate with request rates (the built-in cache exists partly
  for this reason).
- This project is **not** affiliated with, endorsed by, or associated with any of
  the above organisations.

## License

[MIT](LICENSE) © 2026 Romain Flambard and the EndurancePy contributors —
the same permissive license as FastF1.

## Acknowledgements

- **[FastF1](https://github.com/theOehrly/Fast-F1)** by theOehrly & contributors,
  the inspiration and design reference for this project.
- **Al Kamel Systems**, whose public timing archives make endurance data
  analysis possible.
