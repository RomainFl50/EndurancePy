# Public Al Kamel manifests — verification, 2026-11-12

Machine: `PC-FIXE-ROMAIN` (Windows). Repository: `~/Github/EndurancePy`.
Starting commit: `3af41ec3b6a472f53e015c696ed58e7007a5c752`.
Branch: `fix/public-alkamel-manifests`. Reference implementation:
`../wec-dashboard/lib/archives.js`, including the timestamp-folder fix `ca38c07`.

Only simple anonymous curl GET/POST requests were used to investigate the
portals. No cookies, Authorization, browser impersonation, Turnstile calls,
registration or login. Responses and downloaded CSVs stayed in the machine's
temporary directory, outside Git. Tests contain synthetic data only.

## Observed availability

Common settings URL:
`https://5ucg0oksmg.execute-api.us-west-2.amazonaws.com/dev/v2/settings`.

| Portal / request | Result |
| --- | --- |
| POST settings `{"url":"fiawec.alkamelcloud.com"}` | HTTP 200, `requiresAuth: false`, `sections.results.dataAccess: "free"` |
| GET `https://files.alkamelcloud.com/wec/manifests/results.json` | HTTP 200, JSON `seasons_index`, 15 seasons, `01_2011` through `15_2026` |
| GET `https://files.alkamelcloud.com/wec/manifests/results_15_2026.json` | HTTP 200, JSON document tree; 8 events |
| GET Monza Race final-hour Analysis, URL below | HTTP 200; 285,831 transferred bytes with curl compression |
| POST settings `{"url":"elms.alkamelcloud.com"}` | HTTP 200, same public access flags |
| GET `https://files.alkamelcloud.com/elms/manifests/results.json` | HTTP 200, JSON `seasons_index`, 21 season ids `00_2005`–`20_2025`, plus `zz_test` |
| GET `https://files.alkamelcloud.com/elms/manifests/results_20_2025.json` | HTTP 200 **text/html**, SPA shell instead of JSON |
| GET `https://files.alkamelcloud.com/elms/manifests/results_19_2024.json` | HTTP 200 **text/html**, SPA shell instead of JSON |
| POST settings `{"url":"imsa.results.alkamelcloud.com"}` | HTTP 404, no settings entry |
| GET `https://imsa.results.alkamelcloud.com/` | HTTP 200, legacy HTML portal (not the shared Angular application) |

The ELMS season URLs above are taken directly from its public index, not guessed.
Their HTML responses do **not** prove an authentication requirement: they are
invalid manifest responses. The library reports `SessionNotAvailableError` and
does not search for alternate files. An end-to-end ELMS load was therefore not
validated. IMSA's common settings lookup likewise fails explicitly; no new IMSA
JSON endpoint or automatic HTML fallback is assumed. ASLMS/LMC host suffixes
were migrated to `.alkamelcloud.com`, but not validated over the network here.

## JSON contract and URL resolution

Relevant settings fields (selected WEC values):

```json
{
  "clientName": "wec",
  "url": "fiawec.alkamelcloud.com",
  "requiresAuth": false,
  "galleriesUrl": "https://files.alkamelcloud.com/wec/manifests/results.json",
  "sections": { "results": { "dataAccess": "free", "pdfAccess": "free" } }
}
```

Both access checks must pass explicitly before requesting the gallery. Settings
use the cloud domain; the portal's own hostname normalization replaces the old
`.alkamelsystems.com` suffix. EndurancePy also accepts that old suffix in its
internal discovery helpers and normalizes it before the POST.

Observed WEC/ELMS index format (selected WEC entry):

```json
{
  "type": "seasons_index",
  "seasons": [
    { "id": "15_2026", "name": "2026", "manifestUrl": "wec/manifests/results_15_2026.json" }
  ]
}
```

The reader also supports `series_index` with `series[].indexUrl`, whose targets
must be season indexes. This variant is covered synthetically, not observed on
the WEC/ELMS indexes during this check. Conflicting manifest URLs for a season
id raise an error. Nonseason labels such as ELMS's `zz_test` are excluded.

All relative links resolve from the **origin** of `galleriesUrl`:
`https://files.alkamelcloud.com/`, not its `/wec/manifests/` directory. Absolute
HTTPS URLs are retained, spaces encoded once, credentials rejected.

A season manifest has `event` (gallery metadata), `folders[]` (recursive
`children[]`) and `downloadOptions[]`. WEC's root folder contains event folders,
then championship groups, session folders, and sometimes hour folders.
Document leaves have `url`, `name`, `extension` and other metadata. The visible
labels omit numeric prefixes; leaf `date` describes document publication, not
the session start.

The actual Monza Race Analysis URL is:

[Monza 2026 Race, final Hour 6 Analysis](https://files.alkamelcloud.com/wec/results/15_2026/08_AUTODROMO%20NAZIONALE%20DI%20MONZA/689_FIA%20WEC/202611081100_Race/06_Hour%206/23_Analysis_Race_Hour%206.CSV).

Its identity is derived as:

```text
season   = 15_2026
event    = 08_AUTODROMO NAZIONALE DI MONZA
series   = 689_FIA WEC
session  = 202611081100_Race
hour     = 6
filename = 23_Analysis_Race_Hour 6.CSV
kind     = analysis
```

Locate the session by `^\d{12}_`, then take its three preceding segments.
Scan subsequent folders for `Hour N`; do not assume the session is the CSV's
immediate parent. Resolve the latest **numeric** hour separately for Analysis,
Classification and Weather, independent of manifest ordering. The same mechanism
handles `24_Hour 24`; that case is covered by synthetic regression tests.

## Implementation and cache

- `client.download_json(url, payload=...)` uses POST for settings, GET otherwise.
  It is the JSON monkeypatch boundary; `client.download` remains the CSV boundary.
- `manifests.py` validates access, loads season/series indexes, selects only the
  requested season, and recursively collects CSV leaves. Discovery continues to
  return `list[ResultFile]` with the original fields plus `download_url`.
  `ResultFile.url(host)` uses that absolute URL when present; its old behavior is
  retained for records manually constructed without it.
- `fetch_seasons`, `fetch_index`, `fetch_events`, event dates/sessions and session
  loading use this path. Legacy pure HTML/URL helpers remain for compatibility,
  but are not a network fallback.
- `Session.load()` first uses a parsed cache when no source/season was supplied;
  on a miss it resolves the year and uses discovery. Explicit source loading and
  `load(season=...)` remain supported. CSV parsers are unchanged.
- `requests-cache` retains the existing 12-hour HTTP expiry and now includes
  POST bodies in cached settings requests. Stale-on-error is disabled so an HTTP
  failure is not silently replaced with old data. Tests prove repeated POST and
  GET requests are served by the cache without external network access.
- The client uses its honest EndurancePy UA, clears session credentials/cookies,
  disables implicit `.netrc` credentials (and environment proxies via requests'
  `trust_env=False`), does not follow redirects, and raises
  `SessionNotAvailableError` for HTTP/JSON failures. No authentication flow exists.

## Reproduce the public curl checks (PowerShell)

```powershell
$requestPath = Join-Path $env:TEMP 'ep-settings-request.json'
[IO.File]::WriteAllText($requestPath, '{"url":"fiawec.alkamelcloud.com"}')
curl.exe --compressed -sS --max-time 30 -A 'EndurancePy (+https://github.com/RomainFl50/EndurancePy)' -H 'Content-Type: application/json' --data-binary "@$requestPath" -w '\nHTTP %{http_code}\n' 'https://5ucg0oksmg.execute-api.us-west-2.amazonaws.com/dev/v2/settings'
curl.exe --compressed -sS --max-time 30 -A 'EndurancePy (+https://github.com/RomainFl50/EndurancePy)' 'https://files.alkamelcloud.com/wec/manifests/results.json'
curl.exe --compressed -sS --max-time 30 -A 'EndurancePy (+https://github.com/RomainFl50/EndurancePy)' -o "$env:TEMP\ep-wec-season.json" -w 'HTTP %{http_code}\n' 'https://files.alkamelcloud.com/wec/manifests/results_15_2026.json'
```

Repeat the POST with `{"url":"elms.alkamelcloud.com"}`; GET its `galleriesUrl`
and the advertised `manifestUrl` values shown in the availability table. Save
responses under TEMP, and check the body as well as the HTTP status. No `-L`,
cookie jar, browser headers or Turnstile token are required or used.

## Real WEC check and validation limits

Python 3.12.10, temporary cache outside the repository:

```python
import tempfile
import endurancepy as ep

with tempfile.TemporaryDirectory(prefix="ep-public-archives-") as cache:
    ep.Cache.enable_cache(cache)
    try:
        assert "15_2026" in ep.list_seasons("WEC")
        schedule = ep.get_event_schedule(2026, series="WEC")
        session = ep.get_session(2026, series="WEC", event="Monza", session="Race")
        session.load()
        assert not session.laps.empty
        print(len(schedule), len(session.laps), len(session.cars))
    finally:
        # Release SQLite handles before TemporaryDirectory cleanup on Windows.
        ep.Cache.requests_session().close()
```

Observed result: **8 events, 5,660 laps, 35 cars, 314 weather rows, 35 results**.
Discovery selected Analysis/Classification/Weather under `06_Hour 6`. No raw
data was added to Git. Network-marked tests require `ENDURANCEPY_NETWORK=1`;
default unit/example tests are offline.

The initial local PyArrow 26.0.1 build failed loading `_fs` under Windows
application control. Installing the official PyArrow **19.0.1** wheel in `.venv`
resolved this without changing Windows security or project dependency bounds.
The validated local environment uses pandas 3.1.1 and requests-cache 1.3.3.
Validation commands:

- `python -m pytest -q` (also repeated with `-o addopts=''` for counts):
  **173 passed, 3 skipped**; skipped tests are the opt-in network suite.
- `python -m ruff check .`: passed (Ruff 0.17.4).
- `python -m mypy`: passed, 47 source/test files.
- `python -m ruff format --check src tests examples`: passed, 58 files.
- `git diff --check`: passed. CSV parser files were unchanged.

Additional formatting caveat: Ruff 0.17.4's `format --check .` also formats
Markdown code blocks and reports six existing Markdown files. Their unrelated
examples were not reformatted as part of this repair. The broader CI formatter
check should be reviewed before a release; the requested lint/type/test checks
above pass.

No release version bump, tag, push, merge or PyPI publication was performed.
