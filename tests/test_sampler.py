"""Tests for vaultdiff.sampler."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.sampler import SampleConfig, SampleReport, sample_diffs


def _diff(path: str) -> SecretDiff:
    return SecretDiff(path=path, changed={}, only_in_left={}, only_in_right={})


DIFFS = [_diff(f"secret/path/{i}") for i in range(20)]


def test_sample_empty_list_returns_empty_report():
    report = sample_diffs([], SampleConfig(max_paths=5))
    assert report.total_available == 0
    assert report.sample_size == 0
    assert report.selected == []
    assert report.coverage == 0.0


def test_sample_max_paths_respected():
    report = sample_diffs(DIFFS, SampleConfig(max_paths=5, seed=42))
    assert report.sample_size == 5
    assert len(report.selected) == 5


def test_sample_max_paths_capped_at_total():
    report = sample_diffs(DIFFS[:3], SampleConfig(max_paths=100, seed=0))
    assert report.sample_size == 3
    assert report.total_available == 3


def test_sample_fraction_used_when_set():
    report = sample_diffs(DIFFS, SampleConfig(fraction=0.5, seed=1))
    assert report.sample_size == 10


def test_sample_fraction_rounds_to_at_least_one():
    report = sample_diffs(DIFFS[:3], SampleConfig(fraction=0.1, seed=0))
    assert report.sample_size >= 1


def test_sample_fraction_invalid_raises():
    with pytest.raises(ValueError, match="fraction"):
        sample_diffs(DIFFS, SampleConfig(fraction=1.5))


def test_sample_seed_produces_reproducible_results():
    r1 = sample_diffs(DIFFS, SampleConfig(max_paths=5, seed=99))
    r2 = sample_diffs(DIFFS, SampleConfig(max_paths=5, seed=99))
    assert [d.path for d in r1.selected] == [d.path for d in r2.selected]


def test_sample_different_seeds_differ():
    r1 = sample_diffs(DIFFS, SampleConfig(max_paths=5, seed=1))
    r2 = sample_diffs(DIFFS, SampleConfig(max_paths=5, seed=2))
    # With 20 paths and k=5 it is astronomically unlikely both draws are identical
    assert [d.path for d in r1.selected] != [d.path for d in r2.selected]


def test_coverage_calculation():
    report = sample_diffs(DIFFS, SampleConfig(max_paths=4, seed=0))
    assert report.coverage == pytest.approx(4 / 20)


def test_to_dict_contains_expected_keys():
    report = sample_diffs(DIFFS[:5], SampleConfig(max_paths=3, seed=7))
    d = report.to_dict()
    assert set(d.keys()) == {"total_available", "sample_size", "coverage", "seed", "paths"}
    assert d["total_available"] == 5
    assert d["sample_size"] == 3
    assert isinstance(d["paths"], list)


def test_sample_config_from_dict():
    cfg = SampleConfig.from_dict({"seed": 42, "max_paths": 7, "fraction": "0.25"})
    assert cfg.seed == 42
    assert cfg.max_paths == 7
    assert cfg.fraction == pytest.approx(0.25)


def test_sample_config_from_dict_defaults():
    cfg = SampleConfig.from_dict({})
    assert cfg.seed is None
    assert cfg.max_paths == 10
    assert cfg.fraction is None
