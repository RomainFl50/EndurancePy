"""Run the (network-style) examples offline by faking the download layer.

The examples use the real ``Session.load(season=...)`` workflow; here the HTTP
download is monkeypatched to return synthetic fixtures, so the examples are
exercised in CI without network access and without bundling Al Kamel data.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

import endurancepy as ep
from endurancepy.cache import Cache
from endurancepy.core import Session

_EXAMPLES = Path(__file__).parents[1] / "examples"
_FIXTURES = Path(__file__).parent / "fixtures"
_ANALYSIS = (_FIXTURES / "analysis_sample.csv").read_bytes()
_WEATHER = (_FIXTURES / "weather_sample.csv").read_bytes()

# A synthetic season index listing the Spa race's Analysis and Weather files.
_BASE = "Results/08_2018-2019/07_SPA FRANCORCHAMPS/267_FIA WEC/201905041330_Race/Hour 6"
_INDEX_HTML = "".join(
    f'<a href="{_BASE}/{name}">x</a>'
    for name in ("23_Analysis_Race_Hour 6.CSV", "26_Weather_Race_Hour 6.CSV")
)


def _fake_download(url: str) -> bytes:
    if "?season=" in url:
        return _INDEX_HTML.encode()
    if "Analysis" in url:
        return _ANALYSIS
    if "Weather" in url:
        return _WEATHER
    raise AssertionError(f"unexpected download: {url}")


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, _EXAMPLES / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Session:
    monkeypatch.setattr("endurancepy.alkamel.client.download", _fake_download)
    Cache.enable_cache(tmp_path)
    loaded = ep.get_session(2019, "WEC", "Spa", "Race")
    loaded.load(season="08_2018-2019")
    return loaded


def test_examples_import() -> None:
    # Importing exercises top-level code of every example (incl. network-only ones)
    for name in ("quickstart", "schedule_example", "lap_analysis"):
        _load(name)


def test_quickstart(session: Session, capsys: pytest.CaptureFixture[str]) -> None:
    _load("quickstart").summarise(session)
    assert "Fastest lap" in capsys.readouterr().out


def test_lap_analysis(session: Session, capsys: pytest.CaptureFixture[str]) -> None:
    laps = _load("lap_analysis").analyse(session)
    assert len(laps) == 11
    out = capsys.readouterr().out
    assert "Stints" in out and "Classification" in out


def test_standings_example(
    session: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    standings = _load("standings_example").compute([session.results, session.results])
    assert len(standings) == 3
    assert "Overall standings" in capsys.readouterr().out


def test_plot_pace_by_class(session: Session, tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    output = _load("plot_pace_by_class").plot(session, tmp_path / "pace.png")
    assert output.exists() and output.stat().st_size > 0


def test_plot_lap_evolution(session: Session, tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    output = _load("plot_lap_evolution").plot(session, tmp_path / "evo.png")
    assert output.exists() and output.stat().st_size > 0
