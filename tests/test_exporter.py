"""Tests for vaultdiff.exporter."""

from __future__ import annotations

import csv
import io
import json
import os
import tempfile

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.exporter import export_diffs_csv, export_diffs_json, write_export


def _make_diff(
    path: str = "secret/app",
    changed=None,
    only_left=None,
    only_right=None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed=changed or {},
        only_in_left=only_left or {},
        only_in_right=only_right or {},
    )


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def test_export_json_empty():
    result = export_diffs_json([])
    assert json.loads(result) == []


def test_export_json_changed_key():
    diff = _make_diff(changed={"DB_PASS": ("old", "new")})
    data = json.loads(export_diffs_json([diff]))
    assert len(data) == 1
    assert data[0]["path"] == "secret/app"
    assert data[0]["changed"] == [{"key": "DB_PASS", "left": "old", "right": "new"}]


def test_export_json_only_in_left():
    diff = _make_diff(only_left={"OLD_KEY": "val"})
    data = json.loads(export_diffs_json([diff]))
    assert data[0]["only_in_left"] == [{"key": "OLD_KEY", "value": "val"}]
    assert data[0]["only_in_right"] == []


def test_export_json_only_in_right():
    diff = _make_diff(only_right={"NEW_KEY": "val"})
    data = json.loads(export_diffs_json([diff]))
    assert data[0]["only_in_right"] == [{"key": "NEW_KEY", "value": "val"}]


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def test_export_csv_header_only_when_no_diffs():
    result = export_diffs_csv([])
    rows = list(csv.reader(io.StringIO(result)))
    assert rows == [["path", "change_type", "key", "left_value", "right_value"]]


def test_export_csv_changed_row():
    diff = _make_diff(changed={"API_KEY": ("abc", "xyz")})
    result = export_diffs_csv([diff])
    rows = list(csv.reader(io.StringIO(result)))
    assert ["secret/app", "changed", "API_KEY", "abc", "xyz"] in rows


def test_export_csv_removed_and_added_rows():
    diff = _make_diff(only_left={"GONE": "g"}, only_right={"NEW": "n"})
    result = export_diffs_csv([diff])
    rows = list(csv.reader(io.StringIO(result)))
    assert ["secret/app", "removed", "GONE", "g", ""] in rows
    assert ["secret/app", "added", "NEW", "", "n"] in rows


# ---------------------------------------------------------------------------
# write_export
# ---------------------------------------------------------------------------

def test_write_export_json(tmp_path):
    dest = str(tmp_path / "out.json")
    diff = _make_diff(changed={"K": ("a", "b")})
    write_export([diff], "json", dest)
    with open(dest) as fh:
        data = json.load(fh)
    assert data[0]["changed"][0]["key"] == "K"


def test_write_export_csv(tmp_path):
    dest = str(tmp_path / "out.csv")
    diff = _make_diff(only_right={"X": "1"})
    write_export([diff], "csv", dest)
    with open(dest) as fh:
        content = fh.read()
    assert "added" in content


def test_write_export_invalid_format():
    with pytest.raises(ValueError, match="Unsupported export format"):
        write_export([], "xml", "/dev/null")
