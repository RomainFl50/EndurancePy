# CLAUDE.md

EndurancePy loads endurance-racing timing & results data (WEC, ELMS, IMSA, …)
from the Al Kamel archives, with a FastF1-style API. `src/` layout, Hatchling,
Python ≥ 3.10.

## Repository map

```
src/endurancepy/
  core.py            Session / Laps / Lap / SessionResults data objects; the
                     pick_* filters (pick_cars, pick_classes, pick_fastest, …)
  alkamel/           the portal-specific layer:
    client.py          anonymous cache-aware CSV/JSON download; legacy URL helper
    manifests.py       public settings -> season indexes -> document trees
    discovery.py       season/event/session resolution (fuzzy-matched records)
    analysis.py        Analysis CSV -> Laps — the core parser (stints, pit
                       in/out, positions, gaps, Hour, PitTime)
    classification.py  race Classification CSV -> SessionResults
    weather.py         Weather CSV -> weather_data
    timeparse.py       tolerant duration parsing (SS.mmm … H:MM:SS.mmm, >24h)
    headers.py         tolerant Al Kamel CSV reading (BOM, stray spaces, …)
  strategy.py        race-craft tables: pit_stops, stint_summary,
                     driver_summary, lead_changes, battles, time_lost,
                     fuel_corrected
  plotting/          package: colors.py (class/manufacturer/team palettes),
                     style.py (matplotlib setup + lap-time axis), charts.py
                     (interactive Plotly figures + add_track_status /
                     add_day_night overlays)
  events.py          EventSchedule / Event (get_sessions, get_dates, get_race)
  results.py         SessionResults derivation from the laps
  standings.py       compute_standings (points across rounds)
  track_status.py    flag timeline from the laps
  cache.py           two-stage cache: raw HTTP (requests-cache/SQLite) +
                     parsed DataFrames (Parquet), namespaced by PARSER_VERSION
tests/               offline suite + synthetic fixtures;
                     test_integration_network.py is network-marked (self-skips)
examples/            network-based scripts & notebooks, executed offline in CI
                     via the faked download layer (test_examples.py)
docs/                design notes (analyse_fastf1.md), plotting gallery,
                     per-milestone manual test plans (test_plan_<version>.md)
ROADMAP.md           milestone planning; CHANGELOG.md follows Keep a Changelog
```

## Commands

```bash
pip install -e ".[dev,interactive,plot]"   # dev install (plotly + matplotlib extras)
python -m pytest -q                        # full suite; network tests self-skip offline
python -m ruff format . && python -m ruff check .   # ruff also lints notebooks (.ipynb)
python -m mypy                             # targets 3.12 (see pyproject comment)
```

## Conventions

- Lap/sector durations stay `pandas.Timedelta` (FastF1 parity); human-readable
  rendering is a display concern (`format_laptime` / `format_timedelta`).
- **No raw Al Kamel data in the repo.** Fixtures are synthetic; tests and the
  examples run offline by monkeypatching `endurancepy.alkamel.client.download`
  (see `tests/test_examples.py` for the canonical pattern).
- JSON discovery tests patch `endurancepy.alkamel.client.download_json` (keyword
  `payload` for the settings POST); CSV tests still patch `client.download`.
  `tests/conftest.py::mock_manifests` is the synthetic portal fixture.
- Analysis tables (`strategy.py`) accept a `Session`, a `Laps` or a plain
  `DataFrame`, and return typed-but-empty DataFrames instead of raising when
  the input has nothing to say.
- Chart tests guard optional deps with `pytest.importorskip("plotly")` (CI
  installs only `.[dev]`).
- New user-facing work: update `CHANGELOG.md` (under `## [Unreleased]`) and
  `ROADMAP.md` in the same PR.

## Source 2 — public Al Kamel archives (verified 2026-11-12)

- WEC/ELMS use `*.alkamelcloud.com`. POST public settings at
  `https://5ucg0oksmg.execute-api.us-west-2.amazonaws.com/dev/v2/settings`,
  JSON `{"url":"fiawec.alkamelcloud.com"}` (or `elms.alkamelcloud.com`). Require
  `requiresAuth is False` AND `sections.results.dataAccess == "free"`; otherwise
  raise `SessionNotAvailableError`. Never register/login, solve Turnstile, send
  cookies/Authorization or impersonate a browser.
- `galleriesUrl` points to `seasons_index` (`seasons[].manifestUrl`) or
  `series_index` (`series[].indexUrl` -> season indexes). Relative URLs resolve
  from the **origin of galleriesUrl**. Keep season ids as `NN_YYYY` (including
  `NN_YYYY-YYYY` superseasons); nonseason entries like `zz_test` are excluded.
- Season manifests contain recursive `folders[].children[]`; document leaves
  have `url`. Find the timestamped session folder by `^\d{12}_`, then take its
  three parents as season/event/series. Race CSVs may be under `NN_Hour N`;
  select the numerically latest hour per kind, not the last traversal item.
  `ResultFile.download_url` preserves the resolved absolute URL and `url(host)`
  uses it. Existing CSV parsers and the legacy URL helper remain unchanged.
- `Session.load()` without a source/season uses parsed laps from cache, then
  auto-resolves the year and discovers files when the cache is empty.
  `requests-cache` caches settings POSTs as well as GETs. Stale-on-error is
  disabled; HTTP errors, redirects and invalid JSON stop with
  `SessionNotAvailableError`. No guessed endpoint fallback.
- WEC 2026 / Monza Race verified: 5,660 laps, 35 cars, 314 weather rows, final
  Hour 6. ELMS config/index are public, but advertised 2024/2025 season URLs
  returned HTML rather than JSON. IMSA's current host serves a legacy HTML
  portal and has no settings entry at the common endpoint (404). Do not claim
  working discovery for those seasons/IMSA or work around these failures.
- Details, curl reproduction and validation limits:
  [`docs/alkamel-public-manifests.md`](docs/alkamel-public-manifests.md).
  Network tests are opt-in: `ENDURANCEPY_NETWORK=1 python -m pytest -m network`.

## Release methodology (merge → tag → publish)

Generic procedure for every release; `RELEASING.md` is the reference.

1. **Validate before merging.** CI green on the release PR; for a feature
   milestone, run the corresponding manual test plan against a real race
   (e.g. `docs/test_plan_<version>.md` + its notebook in `examples/`).
2. **Cut the release notes in the same PR** as the version bump: move the
   `## [Unreleased]` entries under `## [X.Y.Z] - YYYY-MM-DD`, update the
   compare links at the bottom, bump `version` in `pyproject.toml`. Leave an
   empty `## [Unreleased]` section for the next cycle.
3. **Merge to `main`.** The tag must point at a `main` commit that contains
   the bumped version — the wheel is built from the tagged commit.
4. **Tag and push:**

   ```bash
   git checkout main && git pull origin main
   git tag vX.Y.Z && git push origin vX.Y.Z
   ```

5. **Publishing is automatic.** The `v*` tag triggers
   `.github/workflows/release.yml`: build sdist + wheel, `twine check`, then
   PyPI via Trusted Publishing (OIDC, GitHub environment `pypi` — no token).
6. **Verify:** the PyPI page shows the new version and
   `pip install --upgrade endurancepy` imports with the right `__version__`.
   Optionally create the GitHub Release from the tag with the CHANGELOG section.

Rules:

- **Never move or reuse a pushed tag** — if the release is broken, fix on
  `main` and cut the next patch version (PyPI refuses reused versions anyway).
- A merged-but-never-published milestone **keeps its own dated CHANGELOG
  section** (dated from its merge to `main`, compare-link on the merge commit),
  but gets no retroactive tag or PyPI upload — it first ships in the next
  published version, and both sections cross-reference each other
  (precedent: 0.3.0, first shipped in `v0.4.0`).
- Skipped tags are fine; silent republishes are not.
