"""Tests for vaultdiff.pinner."""
from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock

from vaultdiff.differ import SecretDiff
from vaultdiff.pinner import (
    PinnedKey,
    PinReport,
    check_pins,
    load_pins,
    save_pins,
)


def _make_diff(path="secret/app", changed=None, only_left=None, only_right=None):
    diff = SecretDiff(path=path)
    if changed:
        for key, left, right in changed:
            item = MagicMock(key=key, left_value=left, right_value=right)
            diff.changed.append(item)
    if only_left:
        for key, val in only_left:
            item = MagicMock(key=key, left_value=val, right_value=None)
            diff.only_in_left.append(item)
    if only_right:
        for key, val in only_right:
            item = MagicMock(key=key, left_value=None, right_value=val)
            diff.only_in_right.append(item)
    return diff


def test_check_pins_no_deviation():
    diff = _make_diff(changed=[("DB_PASS", "secret123", "other")])
    report = check_pins(diff, {"DB_PASS": "secret123"})
    assert not report.has_deviations
    assert len(report.pins) == 1
    assert report.pins[0].deviated is False


def test_check_pins_detects_deviation():
    diff = _make_diff(changed=[("DB_PASS", "changed", "other")])
    report = check_pins(diff, {"DB_PASS": "secret123"})
    assert report.has_deviations
    assert report.pins[0].deviated is True
    assert report.pins[0].current_value == "changed"


def test_check_pins_missing_key_deviates():
    diff = _make_diff()  # no data on left
    report = check_pins(diff, {"MISSING_KEY": "expected"})
    assert report.has_deviations
    pin = report.pins[0]
    assert pin.current_value is None
    assert pin.deviated is True


def test_check_pins_only_in_left():
    diff = _make_diff(only_left=[("TOKEN", "abc")])
    report = check_pins(diff, {"TOKEN": "abc"})
    assert not report.has_deviations


def test_pin_report_to_dict_structure():
    diff = _make_diff(changed=[("KEY", "val", "other")])
    report = check_pins(diff, {"KEY": "val"})
    d = report.to_dict()
    assert "path" in d
    assert "has_deviations" in d
    assert "pins" in d
    assert isinstance(d["pins"], list)


def test_pinned_key_to_dict():
    pk = PinnedKey(key="X", pinned_value="a", current_value="b", deviated=True)
    d = pk.to_dict()
    assert d["key"] == "X"
    assert d["deviated"] is True


def test_save_and_load_pins(tmp_path):
    pins = {"secret/app": {"FOO": "bar", "BAZ": "qux"}}
    out = str(tmp_path / "pins.json")
    save_pins(pins, out)
    loaded = load_pins(out)
    assert loaded == pins


def test_load_pins_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_pins(str(tmp_path / "nonexistent.json"))


def test_check_pins_multiple_keys_sorted():
    diff = _make_diff(
        changed=[("Z_KEY", "z", "x"), ("A_KEY", "a", "b")]
    )
    report = check_pins(diff, {"Z_KEY": "z", "A_KEY": "wrong"})
    keys = [p.key for p in report.pins]
    assert keys == sorted(keys)
    assert report.has_deviations  # A_KEY deviates
