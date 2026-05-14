"""Tests for vaultdiff.freezer."""
import json
import time
from pathlib import Path

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.freezer import (
    FrozenEntry,
    FreezeReport,
    freeze_diffs,
    save_freeze,
    load_freeze,
)


def _diff(path="secret/app", changed=None, left=None, right=None):
    return SecretDiff(
        path=path,
        changed_keys=changed or {},
        only_in_left=left or {},
        only_in_right=right or {},
    )


def test_frozen_entry_has_differences_false_when_clean():
    entry = FrozenEntry(path="p", changed_keys=[], only_in_left=[], only_in_right=[])
    assert not entry.has_differences()


def test_frozen_entry_has_differences_true_when_changed():
    entry = FrozenEntry(path="p", changed_keys=["k"], only_in_left=[], only_in_right=[])
    assert entry.has_differences()


def test_frozen_entry_to_dict_keys():
    entry = FrozenEntry(
        path="secret/x", changed_keys=["a"], only_in_left=["b"], only_in_right=[],
        frozen_at=1000.0,
    )
    d = entry.to_dict()
    assert d["path"] == "secret/x"
    assert d["changed_keys"] == ["a"]
    assert d["only_in_left"] == ["b"]
    assert d["only_in_right"] == []
    assert d["frozen_at"] == 1000.0


def test_frozen_entry_roundtrip():
    entry = FrozenEntry(
        path="secret/y", changed_keys=["x"], only_in_left=[], only_in_right=["z"],
        frozen_at=42.0,
    )
    restored = FrozenEntry.from_dict(entry.to_dict())
    assert restored.path == entry.path
    assert restored.changed_keys == entry.changed_keys
    assert restored.frozen_at == entry.frozen_at


def test_freeze_diffs_captures_all_paths():
    diffs = [
        _diff("secret/a", changed={"k": ("v1", "v2")}),
        _diff("secret/b"),
    ]
    report = freeze_diffs(diffs, label="test-run")
    assert len(report.entries) == 2
    assert report.label == "test-run"
    assert report.entries[0].path == "secret/a"
    assert "k" in report.entries[0].changed_keys


def test_freeze_report_dirty_entries_filters_clean():
    diffs = [
        _diff("secret/a", changed={"k": ("v1", "v2")}),
        _diff("secret/b"),
    ]
    report = freeze_diffs(diffs)
    dirty = report.dirty_entries()
    assert len(dirty) == 1
    assert dirty[0].path == "secret/a"


def test_save_and_load_freeze(tmp_path):
    diffs = [_diff("secret/a", right={"new_key": "val"})]
    report = freeze_diffs(diffs, label="ci")
    dest = str(tmp_path / "freeze.json")
    save_freeze(report, dest)
    loaded = load_freeze(dest)
    assert loaded is not None
    assert loaded.label == "ci"
    assert len(loaded.entries) == 1
    assert loaded.entries[0].path == "secret/a"
    assert "new_key" in loaded.entries[0].only_in_right


def test_load_freeze_missing_file_returns_none(tmp_path):
    result = load_freeze(str(tmp_path / "nonexistent.json"))
    assert result is None


def test_freeze_report_to_dict_structure():
    report = FreezeReport(
        entries=[FrozenEntry("p", ["k"], [], [], frozen_at=1.0)],
        label="lbl",
    )
    d = report.to_dict()
    assert d["label"] == "lbl"
    assert isinstance(d["entries"], list)
    assert d["entries"][0]["path"] == "p"
