"""Run the offline examples against the synthetic fixture so they don't rot."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

_EXAMPLES = Path(__file__).parents[1] / "examples"
_FIXTURE = Path(__file__).parent / "fixtures" / "analysis_sample.csv"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, _EXAMPLES / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lap_analysis_runs(capsys: pytest.CaptureFixture[str]) -> None:
    laps = _load("lap_analysis").analyse(_FIXTURE)
    assert len(laps) == 11
    out = capsys.readouterr().out
    assert "Classification" in out
    assert "Stints" in out


def test_standings_example_runs(capsys: pytest.CaptureFixture[str]) -> None:
    standings = _load("standings_example").compute(_FIXTURE)
    assert len(standings) == 3  # three cars in the fixture
    assert "Points" in standings.columns
    assert "Overall standings" in capsys.readouterr().out


def test_plot_pace_by_class(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    output = _load("plot_pace_by_class").plot(_FIXTURE, tmp_path / "pace.png")
    assert output.exists() and output.stat().st_size > 0


def test_plot_lap_evolution(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    output = _load("plot_lap_evolution").plot(_FIXTURE, tmp_path / "evo.png")
    assert output.exists() and output.stat().st_size > 0
