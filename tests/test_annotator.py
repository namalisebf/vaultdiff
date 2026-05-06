"""Tests for vaultdiff.annotator."""

from __future__ import annotations

import pytest

from vaultdiff.annotator import (
    AnnotationConfig,
    AnnotationRule,
    AnnotatedPath,
    annotate_diffs,
)
from vaultdiff.differ import SecretDiff


def _diff(changed=None, left=None, right=None) -> SecretDiff:
    return SecretDiff(
        changed_keys=changed or {},
        only_in_left=left or {},
        only_in_right=right or {},
    )


# ---------------------------------------------------------------------------
# AnnotationRule
# ---------------------------------------------------------------------------

def test_annotation_rule_glob_matches():
    rule = AnnotationRule(pattern="secret/prod/*", note="production path", mode="glob")
    assert rule.matches("secret/prod/db")
    assert not rule.matches("secret/staging/db")


def test_annotation_rule_regex_matches():
    rule = AnnotationRule(pattern=r"secret/(prod|live)/", note="live env", mode="regex")
    assert rule.matches("secret/prod/api")
    assert rule.matches("secret/live/api")
    assert not rule.matches("secret/staging/api")


# ---------------------------------------------------------------------------
# AnnotationConfig.from_dict
# ---------------------------------------------------------------------------

def test_annotation_config_from_dict():
    data = {
        "rules": [
            {"pattern": "secret/prod/*", "note": "production"},
            {"pattern": r".*sensitive.*", "note": "sensitive path", "mode": "regex"},
        ]
    }
    config = AnnotationConfig.from_dict(data)
    assert len(config.rules) == 2
    assert config.rules[0].mode == "glob"
    assert config.rules[1].mode == "regex"


def test_annotation_config_from_dict_empty():
    config = AnnotationConfig.from_dict({})
    assert config.rules == []


# ---------------------------------------------------------------------------
# annotate_diffs
# ---------------------------------------------------------------------------

def test_annotate_diffs_no_rules_produces_empty_notes():
    config = AnnotationConfig()
    results = annotate_diffs([("secret/prod/db", _diff())], config)
    assert len(results) == 1
    assert results[0].notes == []
    assert not results[0].has_notes()


def test_annotate_diffs_single_matching_rule():
    config = AnnotationConfig(
        rules=[AnnotationRule(pattern="secret/prod/*", note="production")]
    )
    results = annotate_diffs([("secret/prod/db", _diff())], config)
    assert results[0].notes == ["production"]
    assert results[0].has_notes()


def test_annotate_diffs_multiple_rules_can_match():
    config = AnnotationConfig(
        rules=[
            AnnotationRule(pattern="secret/prod/*", note="production"),
            AnnotationRule(pattern="secret/*/db", note="database"),
        ]
    )
    results = annotate_diffs([("secret/prod/db", _diff())], config)
    assert set(results[0].notes) == {"production", "database"}


def test_annotate_diffs_non_matching_path_gets_no_notes():
    config = AnnotationConfig(
        rules=[AnnotationRule(pattern="secret/prod/*", note="production")]
    )
    results = annotate_diffs([("secret/staging/db", _diff())], config)
    assert results[0].notes == []


def test_annotated_path_to_dict_includes_has_differences():
    diff = _diff(changed={"KEY": ("old", "new")})
    ap = AnnotatedPath(path="secret/prod/db", diff=diff, notes=["production"])
    d = ap.to_dict()
    assert d["path"] == "secret/prod/db"
    assert d["notes"] == ["production"]
    assert d["has_differences"] is True


def test_annotate_diffs_returns_all_paths():
    config = AnnotationConfig()
    pairs = [
        ("secret/prod/a", _diff()),
        ("secret/staging/a", _diff()),
        ("secret/dev/a", _diff()),
    ]
    results = annotate_diffs(pairs, config)
    assert len(results) == 3
    assert [r.path for r in results] == ["secret/prod/a", "secret/staging/a", "secret/dev/a"]
