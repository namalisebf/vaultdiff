"""Integration tests for collector — verifies end-to-end collect_diffs behaviour."""
from __future__ import annotations

from vaultdiff.differ import SecretDiff
from vaultdiff.collector import collect_diffs, CollectedEntry, CollectionReport


def _diff(path, changed=None, left=None, right=None):
    return SecretDiff(
        path=path,
        changed_keys=changed or {},
        only_in_left=left or {},
        only_in_right=right or {},
    )


def test_all_clean_paths_produce_zero_dirty_count():
    diffs = [_diff(f"secret/svc{i}") for i in range(5)]
    report = collect_diffs(diffs)
    assert report.dirty_paths == 0
    assert report.clean_paths == 5


def test_mixed_paths_dirty_count_is_accurate():
    diffs = [
        _diff("secret/a"),
        _diff("secret/b", changed={"k": ("x", "y")}),
        _diff("secret/c", left={"gone": "v"}),
        _diff("secret/d"),
    ]
    report = collect_diffs(diffs)
    assert report.dirty_paths == 2
    assert report.clean_paths == 2


def test_entry_order_preserved():
    paths = ["secret/z", "secret/a", "secret/m"]
    diffs = [_diff(p) for p in paths]
    report = collect_diffs(diffs)
    assert [e.path for e in report.entries] == paths


def test_collection_report_is_dataclass_instance():
    report = collect_diffs([])
    assert isinstance(report, CollectionReport)


def test_collected_entry_is_dataclass_instance():
    report = collect_diffs([_diff("secret/x")])
    assert isinstance(report.entries[0], CollectedEntry)


def test_to_dict_is_json_serialisable():
    import json
    diffs = [
        _diff("secret/a", changed={"pw": ("old", "new")}),
        _diff("secret/b"),
    ]
    report = collect_diffs(diffs)
    serialised = json.dumps(report.to_dict())
    data = json.loads(serialised)
    assert data["total_paths"] == 2
