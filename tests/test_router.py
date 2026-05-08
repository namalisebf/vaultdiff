"""Tests for vaultdiff.router."""
from unittest.mock import MagicMock

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.router import RouteConfig, RouteRule, RouteReport, route_diffs


def _diff(path: str, changed=None) -> SecretDiff:
    d = MagicMock(spec=SecretDiff)
    d.path = path
    d.has_differences.return_value = bool(changed)
    d.changed_keys = changed or {}
    d.only_in_left = {}
    d.only_in_right = {}
    return d


def test_route_empty_diffs_returns_empty_report():
    config = RouteConfig()
    report = route_diffs([], config)
    assert report.routes == {}
    assert report.destinations == []


def test_route_no_rules_all_go_to_default():
    diffs = [_diff("secret/a"), _diff("secret/b")]
    config = RouteConfig(default_destination="default")
    report = route_diffs(diffs, config)
    assert "default" in report.destinations
    assert len(report.diffs_for("default")) == 2


def test_route_prefix_rule_assigns_correct_destination():
    diffs = [_diff("prod/db"), _diff("staging/db")]
    config = RouteConfig(
        rules=[RouteRule(destination="production", prefix="prod/")],
        default_destination="other",
    )
    report = route_diffs(diffs, config)
    assert [d.path for d in report.diffs_for("production")] == ["prod/db"]
    assert [d.path for d in report.diffs_for("other")] == ["staging/db"]


def test_route_glob_rule_matches_pattern():
    diffs = [_diff("secrets/prod/api"), _diff("secrets/dev/api")]
    config = RouteConfig(
        rules=[RouteRule(destination="prod-bucket", glob="secrets/prod/*")],
        default_destination="dev-bucket",
    )
    report = route_diffs(diffs, config)
    assert len(report.diffs_for("prod-bucket")) == 1
    assert report.diffs_for("prod-bucket")[0].path == "secrets/prod/api"


def test_route_regex_rule_matches():
    diffs = [_diff("app/v2/config"), _diff("app/v1/config")]
    config = RouteConfig(
        rules=[RouteRule(destination="v2", regex=r"/v2/")],
        default_destination="legacy",
    )
    report = route_diffs(diffs, config)
    assert len(report.diffs_for("v2")) == 1
    assert report.diffs_for("legacy")[0].path == "app/v1/config"


def test_route_first_matching_rule_wins():
    diffs = [_diff("prod/db")]
    config = RouteConfig(
        rules=[
            RouteRule(destination="first", prefix="prod/"),
            RouteRule(destination="second", prefix="prod/"),
        ],
        default_destination="default",
    )
    report = route_diffs(diffs, config)
    assert len(report.diffs_for("first")) == 1
    assert report.diffs_for("second") == []


def test_route_config_from_dict():
    data = {
        "rules": [
            {"destination": "critical", "prefix": "prod/"},
            {"destination": "staging", "glob": "stg/*"},
        ],
        "default_destination": "misc",
    }
    config = RouteConfig.from_dict(data)
    assert len(config.rules) == 2
    assert config.default_destination == "misc"
    assert config.rules[0].destination == "critical"
    assert config.rules[1].glob == "stg/*"


def test_route_config_from_dict_empty():
    config = RouteConfig.from_dict({})
    assert config.rules == []
    assert config.default_destination == "default"


def test_to_dict_lists_paths_per_destination():
    d1 = _diff("prod/a")
    d2 = _diff("dev/b")
    config = RouteConfig(
        rules=[RouteRule(destination="prod", prefix="prod/")],
        default_destination="dev",
    )
    report = route_diffs([d1, d2], config)
    result = report.to_dict()
    assert result["prod"] == ["prod/a"]
    assert result["dev"] == ["dev/b"]
