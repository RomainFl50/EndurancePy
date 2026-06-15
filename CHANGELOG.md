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

[Unreleased]: https://github.com/RomainFl50/EndurancePy/commits/main
