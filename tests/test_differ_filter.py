"""Tests for VaultDiffer integration with FilterConfig."""
from unittest.mock import MagicMock

import pytest

from vaultdiff.differ import VaultDiffer
from vaultdiff.filter import FilterConfig


def _make_client(secrets: dict):
    client = MagicMock()
    client.read_secret.side_effect = lambda path: secrets.get(path, {})
    client.list_secrets.return_value = list(secrets.keys())
    return client


def test_diff_paths_respects_include_path_filter():
    left = _make_client({
        "secret/prod/db": {"host": "prod-db"},
        "secret/staging/db": {"host": "staging-db"},
    })
    right = _make_client({
        "secret/prod/db": {"host": "prod-db-right"},
        "secret/staging/db": {"host": "staging-db"},
    })
    cfg = FilterConfig(include_paths=["secret/prod/*"])
    differ = VaultDiffer(left, right, filter_config=cfg)

    results = differ.diff_paths(["secret/prod/db", "secret/staging/db"])

    assert len(results) == 1
    assert results[0].path == "secret/prod/db"
    assert results[0].has_differences


def test_diff_paths_respects_exclude_path_filter():
    left = _make_client({
        "secret/prod/db": {"host": "a"},
        "secret/prod/temp": {"host": "b"},
    })
    right = _make_client({
        "secret/prod/db": {"host": "a"},
        "secret/prod/temp": {"host": "c"},
    })
    cfg = FilterConfig(exclude_paths=["secret/prod/temp"])
    differ = VaultDiffer(left, right, filter_config=cfg)

    results = differ.diff_paths(["secret/prod/db", "secret/prod/temp"])

    assert len(results) == 1
    assert results[0].path == "secret/prod/db"
    assert not results[0].has_differences


def test_diff_secret_excludes_keys():
    left = _make_client({"secret/prod/db": {"host": "db", "password": "s3cr3t"}})
    right = _make_client({"secret/prod/db": {"host": "db", "password": "changed"}})
    cfg = FilterConfig(exclude_keys=["password"])
    differ = VaultDiffer(left, right, filter_config=cfg)

    result = differ.diff_secret("secret/prod/db")

    assert not result.has_differences


def test_diff_secret_includes_only_matching_keys():
    left = _make_client({"secret/prod/db": {"host": "db", "port": "5432", "password": "x"}})
    right = _make_client({"secret/prod/db": {"host": "db-new", "port": "5432", "password": "y"}})
    cfg = FilterConfig(include_keys=["host"])
    differ = VaultDiffer(left, right, filter_config=cfg)

    result = differ.diff_secret("secret/prod/db")

    assert "host" in result.changed
    assert "port" not in result.changed
    assert "password" not in result.changed


def test_diff_recursive_applies_path_filter():
    left = _make_client({
        "secret/prod/a": {"k": "1"},
        "secret/prod/b": {"k": "2"},
    })
    right = _make_client({
        "secret/prod/a": {"k": "1"},
        "secret/prod/b": {"k": "99"},
    })
    cfg = FilterConfig(exclude_paths=["secret/prod/b"])
    differ = VaultDiffer(left, right, filter_config=cfg)

    results = differ.diff_recursive("secret/prod")

    assert all(r.path != "secret/prod/b" for r in results)
    assert len(results) == 1
