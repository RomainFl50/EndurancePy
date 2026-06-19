# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Interactive plotting (0.3.0, in progress).** `plotting.plot_strategy(session)`
  builds an interactive **stint/strategy chart** (Plotly): one horizontal bar per
  stint, per car, coloured by class, with the gaps between a car's bars showing
  its pit stops and the hover giving the stint's driver and lap range. Returns a
  native `plotly.graph_objects.Figure`. Plotly is the new optional `interactive`
  extra (`pip install endurancepy[interactive]`). The `plotting` module is now a
  package (`colors` / `style` / `charts`); all existing names are unchanged.
  Example: [`examples/plot_strategy.py`](examples/plot_strategy.py).

### Planned

- **0.3.0 will focus on plotting** — ready-made chart helpers (strategy/stint
  Gantt, race trace, pace, lap evolution, gaps), a colour/style system beyond the
  current class/manufacturer colours, lap-time axis formatting and a track-status
  overlay. See [`ROADMAP.md`](ROADMAP.md) for the full plan and the plotting
  library evaluation.

## [0.2.0] - 2026-06-18

### Added

- `format_timedelta` / `format_laptime` render a duration as a readable
  `M:SS.mmm` (or `H:MM:SS.mmm`) instead of pandas' verbose
  `0 days 00:01:58.056000`. Lap/sector times stay `Timedelta` (FastF1 parity);
  formatting is a display concern. Used across the examples.
- `set_log_level` now also attaches a console (stderr) handler by default, so
  `ep.set_log_level("INFO")` actually surfaces logs; `enable_console_logging`
  exposes that directly. Loading/discovery now emit INFO logs (events found,
  event/session matched, files resolved, laps parsed, each download). All
  examples enable INFO logging so progress is visible.

### Fixed

- Pace / lap-evolution plots came out **empty** for older seasons (e.g.
  2018-2019), whose Analysis CSV has no per-lap flag column: green-flag
  filtering dropped every lap. The examples now fall back to all non-pit laps
  when no `GF` flag is present (and the pace plot trims to laps within 107% of
  each class best for a meaningful distribution).

- `get_event_schedule` now lists **all** events of a season (parsed from the
  season page's event menu), not just the last/expanded one. Loading a session
  fetches that event's own page (`&evvent=`), so any event of the season can be
  loaded — previously only the most recent event was discoverable.
- An event's session schedule is now populated on demand: `Event.get_sessions()`
  fetches the event's own page and returns a `DataFrame` (one row per session,
  chronological) with `Session`, `StartTime` (date **and** time of day) and
  `Duration` (the race length, derived from the portal's per-hour folders; `NaT`
  for practice/qualifying, whose length the file index does not encode). The
  schedule's `Sessions` column was empty because the calendar is built from the
  season's event *menu* (event names only); the sessions live on each event's
  page.
- `Event.get_dates()` (backed by `discovery.fetch_event_dates`) resolves the
  span of *dates* a weekend runs over — `(first_day, last_day)`, dates only, no
  time of day — on demand from the event's own page. Same rationale as
  `get_sessions()`: the dates aren't in the season's event menu.

### Added

- `list_seasons(series)` returns the available Al Kamel season ids (parsed from
  the portal's season selector), and `get_event_schedule(year, series)` now
  resolves the season id automatically from the year (the explicit `season=`
  argument remains as an override). Enables browsing events by year/series
  without knowing the internal season id.

### Changed

- Session results are now strictly **per car/crew**: the always-empty
  per-driver columns (`DriverNumber`, `Abbreviation`, `FirstName`, `LastName`,
  `FullName`) were removed — at the classification level the crew is what
  matters, and it is kept as `Crew` (drivers `"; "`-joined). Position/lap
  counters (`Position`, `PositionInClass`, `GridPosition`, `Laps`) are now
  nullable integers (`Int64`) instead of floats, so they read `2`, not `2.0`.
- The event schedule no longer carries the always-empty `EventDate`/`Sessions`
  columns. The calendar is built from the season's event *menu* (names only);
  an event's dates and session schedule each live on the event's own page, so
  they are fetched lazily via `Event.get_dates()` / `Event.get_sessions()`
  instead of forcing a per-event fetch when building the schedule.
- Examples now all load a real session over the network
  (`Session.load(season=...)` / `get_event_schedule`) instead of taking a local
  CSV path. CI still exercises them offline by faking the download layer (no
  bundled Al Kamel data).

## [0.1.0] - 2026-06-16

First release: load endurance racing timing & results data (WEC, ELMS, AsLMS,
Le Mans Cup, IMSA) from the Al Kamel archives, with a FastF1-style API.

### Fixed

- Discovery: decode (`unquote`) the portal's percent-encoded result paths so
  built URLs are encoded exactly once (no more `%2520`), and make event/session
  matching prefer substring containment then `partial_ratio` (short queries like
  `"Spa"` no longer mis-resolve). Verified end-to-end against the live portal.

### Added

- Championship standings (milestone 3.1): `compute_standings(results, ...)`
  aggregates points across rounds into a `Standings` table — configurable points
  system (named / sequence / mapping), `by` car/crew/team/manufacturer, overall
  or `per_class`. A generic calculator, not a replica of any series' exact rules.
  Exposed as `ep.compute_standings` / `ep.Standings`.
- Event schedule (milestone 3.0): `get_event_schedule(year, series, season=...)`
  builds an `EventSchedule` (one row per event: round, name, date, sessions)
  from a season's discovered files; `get_event(...)`, `EventSchedule`
  `get_event_by_round`/`get_event_by_name`, and `Event.get_session`/`get_race`
  (the returned session carries its season so `load()` needs no `season=`).
  `discovery.build_events` / `session_datetime` underpin it.
- Examples (`examples/`): `quickstart.py` and `quickstart.ipynb` (load a real
  session via `season=`), `lap_analysis.py` (offline analysis of a local
  Analysis CSV) and `plot_pace_by_class.py` (green-flag pace box plot). The
  offline examples are executed in the test suite so they don't rot.
- Top-level convenience re-exports: `read_analysis`, `read_classification`,
  `read_weather`.
- Project groundwork: MIT `LICENSE`, `README`, `.gitignore`.
- Design documentation:
  - `docs/analyse_fastf1.md` — exhaustive inventory of FastF1's content and its
    mapping onto endurance / Al Kamel data.
  - `docs/plan_implementation.md` — phase-2 implementation plan.
- Community health files: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, GitHub issue
  templates and a pull request template.
- Continuous integration workflow (ruff, mypy, pytest).
- Package skeleton under `src/endurancepy/` (milestone 2.0): the public API
  surface (`get_session`, `get_event`, `get_event_schedule`, `Cache`, `Series`,
  `set_log_level`), data-object class stubs (`Session`, `Laps`/`Lap`,
  `SessionResults`/`CarResult`, `Event`/`EventSchedule`), the `Series` registry,
  reference column schemas, exceptions, logging, and the Al Kamel parser module
  layout (data loading not implemented yet). Project tooling (`pyproject.toml`
  with Hatchling, ruff, mypy, pytest) and a smoke-test suite.
- Cache and Al Kamel client (milestone 2.1):
  - `Cache`: two-stage on-disk cache — stage 1 raw HTTP via `requests-cache`
    (SQLite), stage 2 parsed `DataFrame`s as Parquet plus JSON metadata,
    namespaced by `PARSER_VERSION`. Includes `enable_cache`, `clear_cache`,
    `get_cache_info`, `set_disabled`/`set_enabled`, `disabled()` context
    manager, `offline_mode`, and dataframe/metadata save/load helpers.
  - `alkamel.client`: `build_results_url` (verified `Results/...` tree, URL
    encoding, optional `Hour N`) and a cache-aware `download`.
  - Offline tests covering URL building, Parquet round-trips and the
    download path.
- Analysis CSV parser (milestone 2.2 — the core):
  - `alkamel.timeparse`: tolerant duration parsing (`SS.mmm` / `M:SS.mmm` /
    `H:MM:SS.mmm`, including the >24h rollover).
  - `alkamel.headers.read_alkamel_csv`: tolerant CSV reading (BOM, leading-space
    headers, trailing separator, all values as stripped strings).
  - `alkamel.analysis.to_laps`/`read_analysis`: map the Analysis CSV to `Laps`
    and derive `Stint`, `PitInTime`/`PitOutTime`, `LapStartTime`, the cumulative
    `SectorNSessionTime`, overall and in-class `Position`, `IsPersonalBest`,
    `IsAccurate` and `DriverChange`. (Gaps, `Hour` and `LapStartDate` need
    session context and are filled later.)
  - `Laps.pick_*` filters implemented: `pick_cars`, `pick_classes`,
    `pick_manufacturers`, `pick_stints`, `pick_drivers`, `pick_teams`,
    `pick_laps`, `pick_fastest`, `pick_quicklaps`, `pick_track_status`,
    `pick_wo_box`, `pick_box_laps`, `pick_accurate`; plus
    `SessionResults.pick_classes`.
  - Synthetic Analysis-CSV fixture and tests (multi-class, multi-driver, a pit
    stop and an FCY lap).
- Session results from laps (milestone 2.3):
  - `results.from_laps`: reconstructs `SessionResults` (one row per car/crew)
    from the laps — final order by laps then total time, overall and per class,
    with each car's `Crew`, `BestLapTime`, lap count and total time. (The
    Classification-CSV parser is deferred until its format is verified.)
  - `Session.results` now derives from `laps` when available; `Session.cars`
    (finishing order) and `Session.get_car` implemented.
  - Added `Crew` and `BestLapTime` to the results schema; tests for the
    derivation and the session car helpers.
- Track-status timeline (milestone 2.4):
  - `track_status.from_laps`: reconstructs the session flag timeline (one row
    per change) from the laps' finish-line flags, with a flag registry mapping
    raw codes (GF/FCY/SC/SF/FF/Code60/…) to readable statuses.
  - `Session.track_status` now derives from `laps` when available.
  - (The Weather-CSV parser is deferred until its format is verified.)
- Session loading (milestone 2.5):
  - `Session.load(source=...)` reads an Analysis CSV from a path, bytes or
    `http(s)` URL into `Session.laps` (results and track status derive from it);
    parsed laps are cached as Parquet and reused on a subsequent `load()`.
  - Raises `SessionNotAvailableError` when no source is given and the laps are
    not cached. (Automatic discovery of remote files and the `Event`/
    `EventSchedule` layer remain to be implemented.)
- Automatic discovery in `Session.load` (milestone 2.9):
  - `Session.load(season="<NN_YYYY>")` downloads the portal `?season=` index,
    fuzzy-matches the event and session names, and downloads the Analysis,
    Classification and Weather CSVs automatically (latest hour for races).
  - `discovery.resolve_session_files` / `fetch_index`; `Series.keyword` to
    select the right series folder.
  - Offline tests for the resolution logic; a `network`-marked end-to-end
    integration test (self-skips when the portal is unreachable) plus a manual
    `integration` GitHub Actions workflow to run it on a networked runner.
- Race Classification parser (milestone 2.8):
  - `alkamel.classification.read_classification`/`to_results`: parse the race
    Classification CSV (`POSITION;NUMBER;TEAM;DRIVER_1..5;VEHICLE;CLASS;STATUS;
    LAPS;TOTAL_TIME;FL_TIME;...`) into `SessionResults`, handling the
    apostrophe time format (`5:44'41.101`) and deriving per-class positions and
    each car's crew/manufacturer. Tolerant of the wider practice/qualifying
    layouts (missing columns left empty).
  - `Session.load(results_source=...)` populates `results` from a Classification
    CSV (otherwise results are derived from the laps).
- Weather parser & file discovery (milestone 2.7), based on the **verified**
  real Al Kamel formats (captured via a one-off GitHub Actions probe, since the
  development sandbox cannot reach the portal):
  - `alkamel.weather.read_weather`/`to_weather`: parse the Weather CSV
    (`TIME_UTC_SECONDS;TIME_UTC_STR;AIR_TEMP;TRACK_TEMP;HUMIDITY;PRESSURE;
    WIND_SPEED;WIND_DIRECTION`) into FastF1-style `weather_data` (`Time`
    relative to the first sample; `Rainfall` not provided).
  - `alkamel.discovery`: parse a portal `?season=` page into structured
    `ResultFile` records (season/event/series/session/hour/kind + URL builder)
    by reading the embedded `Results/...CSV` paths.
  - `Session.load(weather_source=...)` populates `weather_data`.
  - Confirmed the Analysis CSV format (old & modern) and the Classification CSV
    headers (race `05_`, practice `03_`, qualifying `90_`) against real files.
- Plotting colour helpers (milestone 2.6):
  - `plotting.get_class_color` / `get_manufacturer_color` (pure functions
    returning hex colours, case-insensitive, with a default fallback) plus
    `list_classes`/`list_manufacturers` and `setup_mpl` (needs the `plot`
    extra). Colours are organised by class and manufacturer rather than driver.

[Unreleased]: https://github.com/RomainFl50/EndurancePy/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/RomainFl50/EndurancePy/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/RomainFl50/EndurancePy/releases/tag/v0.1.0
