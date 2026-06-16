"""Tests for the plotting colour helpers (no plotting backend required)."""

from __future__ import annotations

import re

import pytest

from endurancepy import plotting

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def test_class_color_case_insensitive() -> None:
    assert plotting.get_class_color("HYPERCAR") == plotting.get_class_color("hypercar")
    assert HEX.match(plotting.get_class_color("LMGT3"))


def test_unknown_class_returns_default() -> None:
    assert plotting.get_class_color("does-not-exist") == plotting.DEFAULT_COLOR


def test_manufacturer_color() -> None:
    assert plotting.get_manufacturer_color("Toyota") == "#EB0A1E"
    assert plotting.get_manufacturer_color(
        "ferrari"
    ) == plotting.get_manufacturer_color("FERRARI")
    assert plotting.get_manufacturer_color("nope") == plotting.DEFAULT_COLOR


def test_registries_are_valid_hex() -> None:
    assert plotting.list_classes()
    assert plotting.list_manufacturers()
    for color in (
        *plotting.CLASS_COLORS.values(),
        *plotting.MANUFACTURER_COLORS.values(),
    ):
        assert HEX.match(color)


def test_setup_mpl_if_available() -> None:
    pytest.importorskip("matplotlib")
    plotting.setup_mpl()  # should not raise when matplotlib is installed
