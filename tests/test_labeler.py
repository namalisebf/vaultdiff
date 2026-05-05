"""Tests for vaultdiff.labeler."""

import pytest
from vaultdiff.labeler import LabelConfig, LabelRule, LabeledPath, Labeler


def _make_labeler(*rules) -> Labeler:
    config = LabelConfig(rules=list(rules))
    return Labeler(config)


def test_label_rule_glob_matches():
    rule = LabelRule(label="prod", pattern="secret/prod/*")
    assert rule.matches("secret/prod/db")
    assert not rule.matches("secret/staging/db")


def test_label_rule_regex_matches():
    rule = LabelRule(label="database", pattern=r".*/db$", mode="regex")
    assert rule.matches("secret/prod/db")
    assert not rule.matches("secret/prod/cache")


def test_label_config_from_dict():
    data = {
        "rules": [
            {"label": "prod", "pattern": "secret/prod/*"},
            {"label": "db", "pattern": r".*/db", "mode": "regex"},
        ]
    }
    config = LabelConfig.from_dict(data)
    assert len(config.rules) == 2
    assert config.rules[0].label == "prod"
    assert config.rules[1].mode == "regex"


def test_label_config_from_dict_empty():
    config = LabelConfig.from_dict({})
    assert config.rules == []


def test_labeler_no_rules_produces_empty_labels():
    labeler = _make_labeler()
    result = labeler.label_path("secret/prod/db")
    assert result.path == "secret/prod/db"
    assert result.labels == []


def test_labeler_single_matching_rule():
    rule = LabelRule(label="prod", pattern="secret/prod/*")
    labeler = _make_labeler(rule)
    result = labeler.label_path("secret/prod/api")
    assert "prod" in result.labels


def test_labeler_multiple_labels_on_one_path():
    r1 = LabelRule(label="prod", pattern="secret/prod/*")
    r2 = LabelRule(label="sensitive", pattern="secret/prod/db")
    labeler = _make_labeler(r1, r2)
    result = labeler.label_path("secret/prod/db")
    assert "prod" in result.labels
    assert "sensitive" in result.labels


def test_label_paths_labels_all():
    rule = LabelRule(label="staging", pattern="secret/staging/*")
    labeler = _make_labeler(rule)
    results = labeler.label_paths(["secret/staging/api", "secret/prod/api"])
    assert results[0].labels == ["staging"]
    assert results[1].labels == []


def test_paths_with_label_filters_correctly():
    r1 = LabelRule(label="prod", pattern="secret/prod/*")
    r2 = LabelRule(label="staging", pattern="secret/staging/*")
    labeler = _make_labeler(r1, r2)
    labeled = labeler.label_paths([
        "secret/prod/db",
        "secret/staging/db",
        "secret/prod/cache",
    ])
    prod_paths = labeler.paths_with_label(labeled, "prod")
    assert len(prod_paths) == 2
    assert all("prod" in lp.labels for lp in prod_paths)


def test_labeled_path_to_dict():
    lp = LabeledPath(path="secret/prod/db", labels=["prod", "sensitive"])
    d = lp.to_dict()
    assert d == {"path": "secret/prod/db", "labels": ["prod", "sensitive"]}
