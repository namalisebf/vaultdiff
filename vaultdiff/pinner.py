"""Pin secret key-value pairs and detect deviations from pinned values."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class PinnedKey:
    key: str
    pinned_value: str
    current_value: Optional[str]
    deviated: bool

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "pinned_value": self.pinned_value,
            "current_value": self.current_value,
            "deviated": self.deviated,
        }


@dataclass
class PinReport:
    path: str
    pins: List[PinnedKey] = field(default_factory=list)

    @property
    def has_deviations(self) -> bool:
        return any(p.deviated for p in self.pins)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "has_deviations": self.has_deviations,
            "pins": [p.to_dict() for p in self.pins],
        }


def load_pins(path: str) -> Dict[str, Dict[str, str]]:
    """Load pinned values from a JSON file keyed by secret path then key."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Pin file not found: {path}")
    with p.open() as fh:
        return json.load(fh)


def save_pins(pins: Dict[str, Dict[str, str]], path: str) -> None:
    """Persist pinned values to a JSON file."""
    with Path(path).open("w") as fh:
        json.dump(pins, fh, indent=2)


def check_pins(diff: SecretDiff, pinned: Dict[str, str]) -> PinReport:
    """Compare a SecretDiff's left-side values against pinned expectations."""
    report = PinReport(path=diff.path)
    all_keys = set(pinned)
    left_data: Dict[str, str] = {}
    for item in diff.changed:
        left_data[item.key] = item.left_value or ""
    for item in diff.only_in_left:
        left_data[item.key] = item.left_value or ""

    for key in sorted(all_keys):
        pinned_val = pinned[key]
        current_val = left_data.get(key)
        deviated = current_val != pinned_val
        report.pins.append(
            PinnedKey(
                key=key,
                pinned_value=pinned_val,
                current_value=current_val,
                deviated=deviated,
            )
        )
    return report
