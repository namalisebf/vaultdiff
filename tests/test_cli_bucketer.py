"""Tests for the bucket CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.bucketer import Bucket, BucketReport
from vaultdiff.cli_bucketer import bucket_command
from vaultdiff.differ import SecretDiff
from vaultdiff.vault_client import VaultClientError


def _clean_diff(path="secret/a"):
    d = SecretDiff(path=path)
    d.changed_keys = {}
    d.only_in_left = {}
    d.only_in_right = {}
    return d


def _patch_deps(diffs=None, client_error=None):
    if diffs is None:
        diffs = [_clean_diff()]

    def _make_client(addr, token):
        if client_error:
            raise client_error
        return MagicMock()

    differ = MagicMock()
    differ.diff_secret.side_effect = diffs

    return patch("vaultdiff.cli_bucketer.VaultClient", side_effect=_make_client), \
           patch("vaultdiff.cli_bucketer.VaultDiffer", return_value=differ)


def test_bucket_text_output_default_bucket():
    runner = CliRunner()
    p1, p2 = _patch_deps(diffs=[_clean_diff("secret/a")])
    with p1, p2:
        result = runner.invoke(bucket_command, [
            "--left-addr", "http://left", "--left-token", "lt",
            "--right-addr", "http://right", "--right-token", "rt",
            "--path", "secret/a",
        ])
    assert result.exit_code == 0
    assert "default" in result.output
    assert "secret/a" in result.output


def test_bucket_json_output():
    runner = CliRunner()
    p1, p2 = _patch_deps(diffs=[_clean_diff("secret/b")])
    with p1, p2:
        result = runner.invoke(bucket_command, [
            "--left-addr", "http://left", "--left-token", "lt",
            "--right-addr", "http://right", "--right-token", "rt",
            "--path", "secret/b",
            "--format", "json",
        ])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert "buckets" in data
    assert "total_paths" in data


def test_bucket_vault_client_error_exits_1():
    runner = CliRunner()
    p1, p2 = _patch_deps(client_error=VaultClientError("bad token"))
    with p1, p2:
        result = runner.invoke(bucket_command, [
            "--left-addr", "http://left", "--left-token", "lt",
            "--right-addr", "http://right", "--right-token", "rt",
            "--path", "secret/a",
        ])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_bucket_multiple_paths_distributed():
    runner = CliRunner()
    diffs = [_clean_diff("prod/a"), _clean_diff("staging/b")]
    p1, p2 = _patch_deps(diffs=diffs)
    with p1, p2:
        result = runner.invoke(bucket_command, [
            "--left-addr", "http://left", "--left-token", "lt",
            "--right-addr", "http://right", "--right-token", "rt",
            "--path", "prod/a", "--path", "staging/b",
            "--rule", "prod:5:prod/",
            "--default-bucket", "other",
        ])
    assert result.exit_code == 0
    assert "prod" in result.output
    assert "other" in result.output
