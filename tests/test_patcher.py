"""Tests for vaultdiff.patcher."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.patcher import PatchOp, PatchPlan, build_patch, build_patches


def _make_diff(
    path="secret/app",
    changed=None,
    only_left=None,
    only_right=None,
):
    diff = MagicMock(spec=SecretDiff)
    diff.path = path
    diff.changed_keys = changed or {}
    diff.only_in_left = only_left or {}
    diff.only_in_right = only_right or {}
    diff.has_differences = bool(
        (changed or {}) or (only_left or {}) or (only_right or {})
    )
    return diff


def test_build_patch_no_differences_returns_empty_plan():
    diff = _make_diff()
    plan = build_patch(diff)
    assert isinstance(plan, PatchPlan)
    assert plan.path == "secret/app"
    assert not plan.has_ops
    assert plan.ops == []


def test_build_patch_changed_key_produces_set_op():
    diff = _make_diff(changed={"DB_PASS": ("old", "new")})
    plan = build_patch(diff)
    assert len(plan.ops) == 1
    op = plan.ops[0]
    assert op.operation == "set"
    assert op.key == "DB_PASS"
    assert op.value == "new"
    assert op.old_value == "old"


def test_build_patch_only_in_right_produces_set_op_without_old_value():
    diff = _make_diff(only_right={"NEW_KEY": "val"})
    plan = build_patch(diff)
    assert len(plan.ops) == 1
    op = plan.ops[0]
    assert op.operation == "set"
    assert op.key == "NEW_KEY"
    assert op.value == "val"
    assert op.old_value is None


def test_build_patch_only_in_left_produces_delete_op():
    diff = _make_diff(only_left={"OLD_KEY": "v"})
    plan = build_patch(diff)
    assert len(plan.ops) == 1
    op = plan.ops[0]
    assert op.operation == "delete"
    assert op.key == "OLD_KEY"
    assert op.value is None


def test_build_patches_skips_clean_diffs():
    clean = _make_diff(path="secret/clean")
    dirty = _make_diff(path="secret/dirty", changed={"K": ("a", "b")})
    plans = build_patches([clean, dirty])
    assert len(plans) == 1
    assert plans[0].path == "secret/dirty"


def test_patch_op_to_dict_includes_value_and_old_value():
    op = PatchOp(operation="set", path="p", key="k", value="v", old_value="o")
    d = op.to_dict()
    assert d["operation"] == "set"
    assert d["value"] == "v"
    assert d["old_value"] == "o"


def test_patch_op_to_dict_omits_none_fields():
    op = PatchOp(operation="delete", path="p", key="k")
    d = op.to_dict()
    assert "value" not in d
    assert "old_value" not in d


def test_patch_plan_to_dict_structure():
    plan = PatchPlan(path="secret/x", ops=[
        PatchOp(operation="delete", path="secret/x", key="K"),
    ])
    d = plan.to_dict()
    assert d["path"] == "secret/x"
    assert len(d["ops"]) == 1
    assert d["ops"][0]["operation"] == "delete"
