"""Integration tests for Dispatcher using real SecretDiff objects."""
from __future__ import annotations

from vaultdiff.differ import SecretDiff
from vaultdiff.dispatcher import DispatchConfig, DispatchRule, Dispatcher


def _make_diff(path: str, changed: list | None = None) -> SecretDiff:
    diff = SecretDiff(path=path)
    if changed:
        for key, old, new in changed:
            diff.changed[key] = (old, new)
    return diff


def test_all_diffs_land_in_default_when_no_rules():
    cfg = DispatchConfig(rules=[], default_handler="default")
    dispatcher = Dispatcher(cfg)
    diffs = [_make_diff("a/b"), _make_diff("c/d")]
    report = dispatcher.dispatch(diffs)
    assert set(report.handler_names()) == {"default"}
    assert len(report.dispatched["default"]) == 2


def test_prefix_rule_separates_environments():
    cfg = DispatchConfig(
        rules=[
            DispatchRule(name="prod", pattern="secret/prod/", mode="prefix"),
            DispatchRule(name="staging", pattern="secret/staging/", mode="prefix"),
        ],
        default_handler="other",
    )
    dispatcher = Dispatcher(cfg)
    diffs = [
        _make_diff("secret/prod/db"),
        _make_diff("secret/staging/db"),
        _make_diff("secret/dev/db"),
    ]
    report = dispatcher.dispatch(diffs)
    assert len(report.dispatched["prod"]) == 1
    assert len(report.dispatched["staging"]) == 1
    assert len(report.dispatched["other"]) == 1


def test_to_dict_lists_paths_per_handler():
    cfg = DispatchConfig(
        rules=[DispatchRule(name="prod", pattern="secret/prod/*")],
        default_handler="other",
    )
    dispatcher = Dispatcher(cfg)
    diffs = [_make_diff("secret/prod/db"), _make_diff("secret/dev/db")]
    report = dispatcher.dispatch(diffs)
    d = report.to_dict()
    assert d["prod"] == ["secret/prod/db"]
    assert d["other"] == ["secret/dev/db"]


def test_run_callback_called_once_per_diff():
    cfg = DispatchConfig(
        rules=[DispatchRule(name="prod", pattern="secret/prod/*")],
        default_handler="default",
    )
    dispatcher = Dispatcher(cfg)
    calls = []
    dispatcher.run(
        [_make_diff("secret/prod/x"), _make_diff("secret/prod/y")],
        handlers={"prod": lambda d: calls.append(d.path)},
    )
    assert calls == ["secret/prod/x", "secret/prod/y"]


def test_run_falls_back_to_default_handler_when_named_missing():
    cfg = DispatchConfig(
        rules=[DispatchRule(name="prod", pattern="secret/prod/*")],
        default_handler="default",
    )
    dispatcher = Dispatcher(cfg)
    calls = []
    # no "prod" key — should fall back to "default"
    dispatcher.run(
        [_make_diff("secret/prod/x")],
        handlers={"default": lambda d: calls.append(d.path)},
    )
    assert calls == ["secret/prod/x"]
