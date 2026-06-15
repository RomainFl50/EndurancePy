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

[Unreleased]: https://github.com/RomainFl50/EndurancePy/commits/main
