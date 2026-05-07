"""Patch generation: produce a minimal set of operations to reconcile two secret states."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class PatchOp:
    operation: str          # "set", "delete", "noop"
    path: str
    key: str
    value: Optional[str] = None
    old_value: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {
            "operation": self.operation,
            "path": self.path,
            "key": self.key,
        }
        if self.value is not None:
            d["value"] = self.value
        if self.old_value is not None:
            d["old_value"] = self.old_value
        return d


@dataclass
class PatchPlan:
    path: str
    ops: List[PatchOp] = field(default_factory=list)

    @property
    def has_ops(self) -> bool:
        return bool(self.ops)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "ops": [op.to_dict() for op in self.ops],
        }


def build_patch(diff: SecretDiff) -> PatchPlan:
    """Build a PatchPlan that transforms *left* state into *right* state."""
    plan = PatchPlan(path=diff.path)

    for key, (left_val, right_val) in diff.changed_keys.items():
        plan.ops.append(PatchOp(
            operation="set",
            path=diff.path,
            key=key,
            value=right_val,
            old_value=left_val,
        ))

    for key, val in diff.only_in_right.items():
        plan.ops.append(PatchOp(
            operation="set",
            path=diff.path,
            key=key,
            value=val,
        ))

    for key in diff.only_in_left:
        plan.ops.append(PatchOp(
            operation="delete",
            path=diff.path,
            key=key,
        ))

    return plan


def build_patches(diffs: List[SecretDiff]) -> List[PatchPlan]:
    """Build patch plans for a list of diffs, skipping clean paths."""
    return [build_patch(d) for d in diffs if d.has_differences]
