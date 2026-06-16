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
    module = _load("lap_analysis")
    laps = module.analyse(_FIXTURE)
    assert len(laps) == 11
    assert "laps" in capsys.readouterr().out


def test_plot_pace_by_class(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    module = _load("plot_pace_by_class")
    output = module.plot(_FIXTURE, tmp_path / "pace.png")
    assert output.exists()
    assert output.stat().st_size > 0
