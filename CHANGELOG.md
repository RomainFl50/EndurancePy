# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

[Unreleased]: https://github.com/RomainFl50/EndurancePy/commits/main
