"""Tests for vaultdiff.mapper."""
import pytest
from vaultdiff.mapper import MapRule, MapperConfig, Mapper, MappedPath


# ---------------------------------------------------------------------------
# MapRule.apply
# ---------------------------------------------------------------------------

def test_map_rule_glob_matches():
    rule = MapRule(pattern="secret/dev/*", replacement="secret/prod/x", mode="glob")
    assert rule.apply("secret/dev/db") == "secret/prod/x"


def test_map_rule_glob_no_match_returns_none():
    rule = MapRule(pattern="secret/dev/*", replacement="secret/prod/x", mode="glob")
    assert rule.apply("secret/staging/db") is None


def test_map_rule_prefix_rewrites_suffix():
    rule = MapRule(pattern="secret/dev/", replacement="secret/prod/", mode="prefix")
    assert rule.apply("secret/dev/api") == "secret/prod/api"


def test_map_rule_prefix_no_match_returns_none():
    rule = MapRule(pattern="secret/dev/", replacement="secret/prod/", mode="prefix")
    assert rule.apply("secret/staging/api") is None


def test_map_rule_regex_captures_group():
    rule = MapRule(pattern=r"secret/(\w+)/db", replacement=r"secret/\1/database", mode="regex")
    assert rule.apply("secret/dev/db") == "secret/dev/database"


def test_map_rule_regex_no_match_returns_none():
    rule = MapRule(pattern=r"secret/(\w+)/db", replacement=r"secret/\1/database", mode="regex")
    assert rule.apply("secret/dev/cache") is None


# ---------------------------------------------------------------------------
# MapperConfig.from_dict
# ---------------------------------------------------------------------------

def test_mapper_config_from_dict():
    cfg = MapperConfig.from_dict({
        "rules": [
            {"pattern": "a/*", "replacement": "b/x"},
            {"pattern": "c/", "replacement": "d/", "mode": "prefix"},
        ]
    })
    assert len(cfg.rules) == 2
    assert cfg.rules[0].mode == "glob"
    assert cfg.rules[1].mode == "prefix"


def test_mapper_config_from_dict_empty():
    cfg = MapperConfig.from_dict({})
    assert cfg.rules == []


# ---------------------------------------------------------------------------
# Mapper.map_path
# ---------------------------------------------------------------------------

def _make_mapper(*rules):
    cfg = MapperConfig(rules=list(rules))
    return Mapper(cfg)


def test_map_path_no_rules_returns_original():
    mapper = _make_mapper()
    result = mapper.map_path("secret/dev/api")
    assert result.original == "secret/dev/api"
    assert result.mapped == "secret/dev/api"
    assert result.rule_applied is False


def test_map_path_first_rule_wins():
    r1 = MapRule(pattern="secret/dev/*", replacement="first", mode="glob")
    r2 = MapRule(pattern="secret/dev/*", replacement="second", mode="glob")
    mapper = _make_mapper(r1, r2)
    result = mapper.map_path("secret/dev/api")
    assert result.mapped == "first"
    assert result.rule_applied is True


def test_map_path_falls_through_to_second_rule():
    r1 = MapRule(pattern="secret/prod/*", replacement="no", mode="glob")
    r2 = MapRule(pattern="secret/dev/", replacement="secret/staging/", mode="prefix")
    mapper = _make_mapper(r1, r2)
    result = mapper.map_path("secret/dev/api")
    assert result.mapped == "secret/staging/api"
    assert result.rule_applied is True


def test_map_paths_returns_one_per_input():
    mapper = _make_mapper()
    results = mapper.map_paths(["a", "b", "c"])
    assert len(results) == 3
    assert all(isinstance(r, MappedPath) for r in results)


def test_mapped_path_to_dict_keys():
    mp = MappedPath(original="a", mapped="b", rule_applied=True)
    d = mp.to_dict()
    assert set(d.keys()) == {"original", "mapped", "rule_applied"}
