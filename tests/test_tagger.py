"""Tests for vaultdiff.tagger."""
import pytest

from vaultdiff.tagger import TagRule, TaggerConfig, Tagger


# ---------------------------------------------------------------------------
# TagRule.matches
# ---------------------------------------------------------------------------

def test_tag_rule_glob_matches():
    rule = TagRule(pattern="secret/prod/*", tags=["prod"])
    assert rule.matches("secret/prod/db")
    assert not rule.matches("secret/staging/db")


def test_tag_rule_regex_matches():
    rule = TagRule(pattern=r"secret/(prod|staging)/.*", tags=["live"], regex=True)
    assert rule.matches("secret/prod/api")
    assert rule.matches("secret/staging/api")
    assert not rule.matches("secret/dev/api")


# ---------------------------------------------------------------------------
# TaggerConfig.from_dict
# ---------------------------------------------------------------------------

def test_tagger_config_from_dict():
    data = {
        "rules": [
            {"pattern": "secret/prod/*", "tags": ["prod", "critical"]},
            {"pattern": r"secret/dev/.*", "tags": ["dev"], "regex": True},
        ]
    }
    cfg = TaggerConfig.from_dict(data)
    assert len(cfg.rules) == 2
    assert cfg.rules[0].tags == ["prod", "critical"]
    assert cfg.rules[1].regex is True


def test_tagger_config_from_dict_empty():
    cfg = TaggerConfig.from_dict({})
    assert cfg.rules == []


# ---------------------------------------------------------------------------
# Tagger.tags_for
# ---------------------------------------------------------------------------

def _make_tagger() -> Tagger:
    cfg = TaggerConfig(
        rules=[
            TagRule(pattern="secret/prod/*", tags=["prod", "critical"]),
            TagRule(pattern="secret/*/db", tags=["database"]),
            TagRule(pattern="secret/dev/*", tags=["dev"]),
        ]
    )
    return Tagger(cfg)


def test_tags_for_single_match():
    tagger = _make_tagger()
    assert tagger.tags_for("secret/dev/api") == ["dev"]


def test_tags_for_multiple_rules_match():
    tagger = _make_tagger()
    tags = tagger.tags_for("secret/prod/db")
    assert "prod" in tags
    assert "critical" in tags
    assert "database" in tags


def test_tags_for_no_match_returns_empty():
    tagger = _make_tagger()
    assert tagger.tags_for("secret/qa/service") == []


def test_tags_for_deduplicates():
    cfg = TaggerConfig(
        rules=[
            TagRule(pattern="secret/prod/*", tags=["prod"]),
            TagRule(pattern="secret/prod/db", tags=["prod", "database"]),
        ]
    )
    tagger = Tagger(cfg)
    tags = tagger.tags_for("secret/prod/db")
    assert tags.count("prod") == 1


# ---------------------------------------------------------------------------
# Tagger.tag_paths / paths_for_tag
# ---------------------------------------------------------------------------

def test_tag_paths_returns_mapping():
    tagger = _make_tagger()
    paths = ["secret/prod/api", "secret/dev/api", "secret/qa/x"]
    result = tagger.tag_paths(paths)
    assert result["secret/prod/api"] == ["prod", "critical"]
    assert result["secret/dev/api"] == ["dev"]
    assert result["secret/qa/x"] == []


def test_paths_for_tag_filters_correctly():
    tagger = _make_tagger()
    paths = ["secret/prod/api", "secret/prod/db", "secret/dev/api"]
    assert tagger.paths_for_tag("prod", paths) == ["secret/prod/api", "secret/prod/db"]
    assert tagger.paths_for_tag("database", paths) == ["secret/prod/db"]
    assert tagger.paths_for_tag("unknown", paths) == []
