"""Tests for vaultdiff.evolver."""
from __future__ import annotations

from unittest.mock import MagicMock

from vaultdiff.differ import SecretDiff
from vaultdiff.evolver import (
    EvolutionPoint,
    EvolutionTrack,
    build_evolution_point,
    evolve_diffs,
)


def _diff(path: str, changed=(), left_only=(), right_only=()) -> SecretDiff:
    d = MagicMock(spec=SecretDiff)
    d.path = path
    d.changed_keys = list(changed)
    d.only_in_left = list(left_only)
    d.only_in_right = list(right_only)
    return d


def test_build_evolution_point_counts_correctly():
    diff = _diff("secret/app", changed=["k1"], left_only=["k2"], right_only=[])
    pt = build_evolution_point("v1", diff)
    assert pt.label == "v1"
    assert pt.changed_keys == 1
    assert pt.only_in_left == 1
    assert pt.only_in_right == 0
    assert pt.total_differences == 2


def test_evolution_point_to_dict():
    pt = EvolutionPoint(label="v1", changed_keys=2, only_in_left=1, only_in_right=0, total_differences=3)
    d = pt.to_dict()
    assert d["label"] == "v1"
    assert d["total_differences"] == 3


def test_evolution_track_is_stable_when_no_change():
    track = EvolutionTrack(path="secret/app")
    track.points = [
        EvolutionPoint("v1", 0, 0, 0, 0),
        EvolutionPoint("v2", 0, 0, 0, 0),
    ]
    assert track.is_stable() is True
    assert track.is_growing() is False


def test_evolution_track_is_growing_when_strictly_increasing():
    track = EvolutionTrack(path="secret/app")
    track.points = [
        EvolutionPoint("v1", 1, 0, 0, 1),
        EvolutionPoint("v2", 2, 0, 0, 2),
        EvolutionPoint("v3", 3, 0, 0, 3),
    ]
    assert track.is_growing() is True
    assert track.is_stable() is False


def test_evolution_track_not_growing_when_decreases():
    track = EvolutionTrack(path="secret/app")
    track.points = [
        EvolutionPoint("v1", 3, 0, 0, 3),
        EvolutionPoint("v2", 1, 0, 0, 1),
    ]
    assert track.is_growing() is False


def test_evolution_track_to_dict_includes_trend_flags():
    track = EvolutionTrack(path="secret/app")
    track.points = [EvolutionPoint("v1", 0, 0, 0, 0)]
    d = track.to_dict()
    assert d["path"] == "secret/app"
    assert "is_growing" in d
    assert "is_stable" in d
    assert len(d["points"]) == 1


def test_evolve_diffs_builds_tracks_per_path():
    d1 = _diff("secret/a", changed=["x"])
    d2 = _diff("secret/b", left_only=["y"])
    labeled = [("v1", [d1, d2])]
    tracks = evolve_diffs(labeled)
    paths = {t.path for t in tracks}
    assert "secret/a" in paths
    assert "secret/b" in paths


def test_evolve_diffs_accumulates_points_across_labels():
    d_v1 = _diff("secret/a", changed=["k"])
    d_v2 = _diff("secret/a", changed=["k", "m"])
    labeled = [("v1", [d_v1]), ("v2", [d_v2])]
    tracks = evolve_diffs(labeled)
    assert len(tracks) == 1
    assert len(tracks[0].points) == 2
    assert tracks[0].points[0].label == "v1"
    assert tracks[0].points[1].label == "v2"


def test_evolve_diffs_empty_returns_empty():
    assert evolve_diffs([]) == []
