"""Tests for vaultdiff.cli_profiler."""
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from vaultdiff.cli_profiler import profile_command
from vaultdiff.differ import SecretDiff
from vaultdiff.vault_client import VaultClientError


def _clean_diff(path="secret/app"):
    return SecretDiff(
        path=path,
        changed_keys=[],
        only_in_left=[],
        only_in_right=[],
        left_data={"key": "val"},
        right_data={"key": "val"},
    )


def _dirty_diff(path="secret/svc"):
    return SecretDiff(
        path=path,
        changed_keys=["token"],
        only_in_left=[],
        only_in_right=[],
        left_data={"token": "old"},
        right_data={"token": "new"},
    )


def _patch_deps(diffs):
    return patch.multiple(
        "vaultdiff.cli_profiler",
        VaultClient=MagicMock(),
        VaultDiffer=MagicMock(
            return_value=MagicMock(
                diff_secret=MagicMock(side_effect=diffs),
                diff_recursive=MagicMock(return_value=diffs),
            )
        ),
    )


BASE_ARGS = [
    "--left-addr", "http://left",
    "--left-token", "lt",
    "--right-addr", "http://right",
    "--right-token", "rt",
]


def test_profile_text_output_stable():
    runner = CliRunner()
    with _patch_deps([_clean_diff()]):
        result = runner.invoke(profile_command, BASE_ARGS + ["--path", "secret/app"])
    assert result.exit_code == 0
    assert "stable" in result.output


def test_profile_json_output():
    runner = CliRunner()
    with _patch_deps([_dirty_diff()]):
        result = runner.invoke(
            profile_command, BASE_ARGS + ["--path", "secret/svc", "--format", "json"]
        )
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["category"] in ("stable", "moderate", "volatile")


def test_profile_vault_client_error_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_profiler.VaultClient", side_effect=VaultClientError("bad")):
        result = runner.invoke(profile_command, BASE_ARGS + ["--path", "secret/app"])
    assert result.exit_code == 1
    assert "Vault connection error" in result.output


def test_profile_recursive_flag():
    runner = CliRunner()
    differ_mock = MagicMock(
        diff_recursive=MagicMock(return_value=[_clean_diff(), _dirty_diff()])
    )
    with patch("vaultdiff.cli_profiler.VaultClient", MagicMock()), \
         patch("vaultdiff.cli_profiler.VaultDiffer", MagicMock(return_value=differ_mock)):
        result = runner.invoke(
            profile_command, BASE_ARGS + ["--path", "secret/", "--recursive"]
        )
    assert result.exit_code == 0
    differ_mock.diff_recursive.assert_called_once_with("secret/")


def test_profile_empty_paths_shows_message():
    runner = CliRunner()
    differ_mock = MagicMock(diff_secret=MagicMock(return_value=_clean_diff()))
    # pass zero paths — click should complain about missing required option
    with patch("vaultdiff.cli_profiler.VaultClient", MagicMock()), \
         patch("vaultdiff.cli_profiler.VaultDiffer", MagicMock(return_value=differ_mock)):
        result = runner.invoke(profile_command, BASE_ARGS)
    assert result.exit_code != 0
