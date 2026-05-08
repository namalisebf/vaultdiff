"""Unit tests for vaultdiff.dispatcher."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.dispatcher import (
    DispatchConfig,
    DispatchReport,
    DispatchRule,
    Dispatcher,
)


def _diff(path: str) -> SecretDiff:
    d = MagicMock(spec=SecretDiff)
    d.path = path
    return d


# ── DispatchRule ────────────────────────────────────────────────────────────

def test_dispatch_rule_glob_matches():
    rule = DispatchRule(name="prod", pattern="secret/prod/*")
    assert rule.matches("secret/prod/db")
    assert not rule.matches("secret/staging/db")


def test_dispatch_rule_prefix_matches():
    rule = DispatchRule(name="infra", pattern="infra/", mode="prefix")
    assert rule.matches("infra/network")
    assert not rule.matches("app/network")


def test_dispatch_rule_regex_matches():
    rule = DispatchRule(name="numbered", pattern=r"env\d+", mode="regex")
    assert rule.matches("env42/secret")
    assert not rule.matches("envX/secret")


# ── DispatchConfig ──────────────────────────────────────────────────────────

def test_dispatch_config_from_dict():
    cfg = DispatchConfig.from_dict({
        "rules": [{"name": "prod", "pattern": "secret/prod/*", "mode": "glob"}],
        "default_handler": "fallback",
    })
    assert len(cfg.rules) == 1
    assert cfg.default_handler == "fallback"


def test_dispatch_config_from_dict_empty():
    cfg = DispatchConfig.from_dict({})
    assert cfg.rules == []
    assert cfg.default_handler == "default"


# ── Dispatcher ──────────────────────────────────────────────────────────────

def test_dispatch_routes_to_matching_rule():
    cfg = DispatchConfig(
        rules=[DispatchRule(name="prod", pattern="secret/prod/*")],
        default_handler="other",
    )
    dispatcher = Dispatcher(cfg)
    report = dispatcher.dispatch([_diff("secret/prod/db"), _diff("secret/dev/db")])
    assert "prod" in report.dispatched
    assert "other" in report.dispatched
    assert report.dispatched["prod"][0].path == "secret/prod/db"
    assert report.dispatched["other"][0].path == "secret/dev/db"


def test_dispatch_all_go_to_default_when_no_rules():
    cfg = DispatchConfig(rules=[], default_handler="default")
    dispatcher = Dispatcher(cfg)
    report = dispatcher.dispatch([_diff("a/b"), _diff("c/d")])
    assert list(report.dispatched.keys()) == ["default"]
    assert len(report.dispatched["default"]) == 2


def test_dispatch_first_matching_rule_wins():
    cfg = DispatchConfig(
        rules=[
            DispatchRule(name="first", pattern="secret/*"),
            DispatchRule(name="second", pattern="secret/prod/*"),
        ]
    )
    dispatcher = Dispatcher(cfg)
    report = dispatcher.dispatch([_diff("secret/prod/db")])
    assert "first" in report.dispatched
    assert "second" not in report.dispatched


def test_dispatch_report_to_dict():
    d = _diff("secret/prod/db")
    report = DispatchReport(dispatched={"prod": [d]})
    result = report.to_dict()
    assert result == {"prod": ["secret/prod/db"]}


def test_run_invokes_handler_for_each_diff():
    cfg = DispatchConfig(
        rules=[DispatchRule(name="prod", pattern="secret/prod/*")],
        default_handler="default",
    )
    dispatcher = Dispatcher(cfg)
    seen = []
    dispatcher.run(
        [_diff("secret/prod/db"), _diff("secret/dev/db")],
        handlers={
            "prod": lambda d: seen.append(("prod", d.path)),
            "default": lambda d: seen.append(("default", d.path)),
        },
    )
    assert ("prod", "secret/prod/db") in seen
    assert ("default", "secret/dev/db") in seen
