# Usage guide

A quick tour of what EndurancePy can do today. The API mirrors
[FastF1](https://github.com/theOehrly/Fast-F1) with an added **series** axis.

> Status: early. Loading works from a local/remote **Analysis CSV**; automatic
> discovery of remote files is not implemented yet, and there is **no car
> telemetry** for endurance racing (no public source). See the README roadmap.

## Install

```bash
pip install -e .            # from a checkout
pip install -e ".[plot]"    # with the plotting extra (matplotlib)
```

## Enable the cache

The cache stores raw downloads and parsed laps (Parquet), so a session is only
parsed once. It is strongly recommended (a 24h race is tens of thousands of laps).

```python
import endurancepy as ep

ep.Cache.enable_cache("./endurancepy-cache")   # directory must exist
```

## Load a session

Point `Session.load` at an Analysis CSV — a local path, raw bytes, or an
`http(s)` URL:

```python
session = ep.get_session(2024, series="WEC", event="Le Mans", session="Race")
session.load(source="path/to/23_Analysis_Race.CSV")

# On a later run, the parsed laps are served from the cache:
session = ep.get_session(2024, series="WEC", event="Le Mans", session="Race")
session.load()                                  # no source -> from cache
```

Supported series: `WEC`, `ELMS`, `ASLMS`, `LMC`, `IMSA` (all timed by Al Kamel).

## Work with laps

`Session.laps` is a `Laps` object — a pandas `DataFrame` with endurance-aware
helpers. Columns include `CarNumber`, `Driver`, `LapNumber`, `LapTime`,
`Sector1/2/3Time`, `Stint`, `PitInTime`/`PitOutTime`, `Class`, `Manufacturer`,
`Position`, `PositionInClass`, `LapAvgSpeed` (km/h), `SpeedST` (speed trap),
`TrackStatus`, `IsAccurate`, `IsPersonalBest`, …

```python
laps = session.laps

laps.pick_cars(["7", "8"])          # by car number
laps.pick_classes("HYPERCAR")        # by class
laps.pick_manufacturers("Toyota")    # by manufacturer
laps.pick_drivers("Kamui KOBAYASHI") # by driver (name or number)
laps.pick_stints(2)                  # by stint
laps.pick_wo_box()                   # exclude in/out laps
laps.pick_accurate()                 # only clean, green-flag laps
laps.pick_track_status("FCY")        # laps under full-course yellow

fastest = laps.pick_classes("HYPERCAR").pick_fastest()   # a single Lap
```

You can also parse a file directly, without a `Session`:

```python
from endurancepy.alkamel.analysis import read_analysis

laps = read_analysis("path/to/23_Analysis_Race.CSV")
```

## Classification & track status

`Session.results` and `Session.track_status` are derived from the laps:

```python
results = session.results            # one row per car/crew
results.pick_classes("LMGT3")        # filter to a class

session.cars                         # car numbers in finishing order
session.get_car("7")                 # a single CarResult

session.track_status                 # green / FCY / SC / code 60 / red timeline
```

`SessionResults` columns include `Position`, `PositionInClass`,
`ClassifiedPosition`, `Laps`, `Time`, `BestLapTime`, `Class`, `Manufacturer`,
`TeamName`, and `Crew` (the car's drivers).

## Plotting colours

Colours are organised by class and manufacturer (not by driver):

```python
from endurancepy import plotting

plotting.get_class_color("HYPERCAR")        # -> "#E10600"
plotting.get_manufacturer_color("Ferrari")  # -> "#DC0000"
plotting.setup_mpl()                         # basic matplotlib styling (plot extra)
```

## Not available (yet)

- **Car telemetry** (speed/throttle/brake/gear/RPM/GPS) — no public source for
  endurance racing.
- **Automatic discovery** of remote result files, and the `Event`/
  `EventSchedule` calendar layer.
- **Classification / weather CSV parsers** — deferred until their exact format
  is verified (results are currently derived from the Analysis CSV).
- **Championship standings**.
