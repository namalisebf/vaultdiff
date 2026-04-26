"""Tests for the VaultDiffer module."""

from unittest.mock import MagicMock

import pytest

from vaultdiff.differ import SecretDiff, VaultDiffer


def _make_client(secrets: dict, listing: dict | None = None) -> MagicMock:
    client = MagicMock()
    client.read_secret.side_effect = lambda path: secrets.get(path, {})
    client.list_secrets.side_effect = lambda path: (listing or {}).get(path, [])
    return client


def test_diff_secret_no_differences():
    data = {"secret/app": {"key": "value", "db": "postgres"}}
    left = _make_client(data)
    right = _make_client(data)
    differ = VaultDiffer(left, right)

    result = differ.diff_secret("secret/app")

    assert isinstance(result, SecretDiff)
    assert not result.has_differences
    assert set(result.unchanged) == {"key", "db"}


def test_diff_secret_detects_changed_values():
    left = _make_client({"secret/app": {"key": "old_value"}})
    right = _make_client({"secret/app": {"key": "new_value"}})
    differ = VaultDiffer(left, right)

    result = differ.diff_secret("secret/app")

    assert result.has_differences
    assert "key" in result.changed
    assert result.changed["key"] == ("old_value", "new_value")


def test_diff_secret_detects_only_in_left():
    left = _make_client({"secret/app": {"extra": "only_here", "shared": "x"}})
    right = _make_client({"secret/app": {"shared": "x"}})
    differ = VaultDiffer(left, right)

    result = differ.diff_secret("secret/app")

    assert result.has_differences
    assert "extra" in result.only_in_left
    assert result.only_in_left["extra"] == "only_here"


def test_diff_secret_detects_only_in_right():
    left = _make_client({"secret/app": {"shared": "x"}})
    right = _make_client({"secret/app": {"shared": "x", "new_key": "added"}})
    differ = VaultDiffer(left, right)

    result = differ.diff_secret("secret/app")

    assert result.has_differences
    assert "new_key" in result.only_in_right


def test_diff_recursive_returns_all_paths():
    listing = {"secret/": ["app", "db"]}
    secrets = {
        "secret/app": {"token": "abc"},
        "secret/db": {"password": "secret"},
    }
    left = _make_client(secrets, listing)
    right = _make_client(secrets, listing)
    differ = VaultDiffer(left, right)

    results = differ.diff_recursive("secret/")

    assert len(results) == 2
    paths = [r.path for r in results]
    assert "secret//app" in paths or any("app" in p for p in paths)


def test_diff_secret_missing_on_both_sides():
    left = _make_client({})
    right = _make_client({})
    differ = VaultDiffer(left, right)

    result = differ.diff_secret("secret/missing")

    assert not result.has_differences
    assert result.unchanged == []
