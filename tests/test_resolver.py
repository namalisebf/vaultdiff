"""Tests for vaultdiff.resolver."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vaultdiff.resolver import ResolvedPath, ResolveReport, resolve_paths
from vaultdiff.vault_client import VaultClientError


def _make_client(data):
    """Return a mock VaultClient whose read_secret returns *data* or raises."""
    client = MagicMock()
    if isinstance(data, Exception):
        client.read_secret.side_effect = data
    else:
        client.read_secret.return_value = data
    return client


def test_resolved_path_present_and_missing():
    rp = ResolvedPath(path="secret/app", envs={"prod": {"k": "v"}, "staging": None})
    assert rp.present_in == ["prod"]
    assert rp.missing_from == ["staging"]


def test_resolved_path_is_consistent_when_same_data():
    rp = ResolvedPath(
        path="secret/app",
        envs={"prod": {"k": "v"}, "staging": {"k": "v"}},
    )
    assert rp.is_consistent is True


def test_resolved_path_is_inconsistent_when_values_differ():
    rp = ResolvedPath(
        path="secret/app",
        envs={"prod": {"k": "v1"}, "staging": {"k": "v2"}},
    )
    assert rp.is_consistent is False


def test_resolved_path_to_dict_keys():
    rp = ResolvedPath(path="secret/app", envs={"prod": {"k": "v"}})
    d = rp.to_dict()
    assert set(d.keys()) == {"path", "envs", "present_in", "missing_from", "is_consistent"}


def test_resolve_paths_reads_all_envs():
    clients = {
        "prod": _make_client({"db": "prod-url"}),
        "staging": _make_client({"db": "staging-url"}),
    }
    report = resolve_paths(clients, ["secret/db"])
    assert len(report.paths) == 1
    rp = report.paths[0]
    assert rp.path == "secret/db"
    assert rp.envs["prod"] == {"db": "prod-url"}
    assert rp.envs["staging"] == {"db": "staging-url"}


def test_resolve_paths_missing_path_stored_as_none():
    clients = {
        "prod": _make_client({"k": "v"}),
        "staging": _make_client(VaultClientError("not found")),
    }
    report = resolve_paths(clients, ["secret/missing"])
    rp = report.paths[0]
    assert rp.envs["prod"] == {"k": "v"}
    assert rp.envs["staging"] is None
    assert "staging" in rp.missing_from


def test_resolve_report_inconsistent_paths():
    clients = {
        "prod": _make_client({"k": "v1"}),
        "staging": _make_client({"k": "v2"}),
    }
    report = resolve_paths(clients, ["secret/app"])
    assert len(report.inconsistent_paths) == 1
    assert len(report.missing_paths) == 0


def test_resolve_report_to_dict_structure():
    clients = {
        "prod": _make_client({"k": "v"}),
        "staging": _make_client({"k": "v"}),
    }
    report = resolve_paths(clients, ["secret/app"])
    d = report.to_dict()
    assert d["total"] == 1
    assert d["inconsistent"] == 0
    assert d["missing"] == 0
    assert isinstance(d["paths"], list)
