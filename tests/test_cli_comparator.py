"""Tests for the `compare` CLI sub-command."""
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli_comparator import compare_command
from vaultdiff.comparator import ComparisonResult
from vaultdiff.differ import SecretDiff
from vaultdiff.vault_client import VaultClientError

BASE_ARGS = [
    "--left-addr", "http://vault-left:8200",
    "--left-token", "tok-left",
    "--right-addr", "http://vault-right:8200",
    "--right-token", "tok-right",
]


def _clean_result(paths=("secret/a",)):
    diffs = {p: SecretDiff({}, {}, {}) for p in paths}
    return ComparisonResult(paths=list(paths), diffs=diffs)


def _patch_deps(result):
    return patch.multiple(
        "vaultdiff.cli_comparator",
        VaultClient=MagicMock(),
        VaultDiffer=MagicMock(),
        Comparator=MagicMock(return_value=MagicMock(
            compare=MagicMock(return_value=result),
            compare_recursive=MagicMock(return_value=result),
        )),
    )


def test_compare_clean_text_output():
    result = _clean_result(["secret/a", "secret/b"])
    runner = CliRunner()
    with _patch_deps(result):
        out = runner.invoke(compare_command, BASE_ARGS + ["--path", "secret/a", "--path", "secret/b"])
    assert out.exit_code == 0
    assert "PASS" in out.output
    assert "CLEAN" in out.output


def test_compare_json_output():
    result = _clean_result(["secret/x"])
    runner = CliRunner()
    with _patch_deps(result):
        out = runner.invoke(compare_command, BASE_ARGS + ["--path", "secret/x", "--format", "json"])
    assert out.exit_code == 0
    assert "\"passed\"" in out.output


def test_compare_exit_code_on_differences():
    diff_result = ComparisonResult(
        paths=["secret/p"],
        diffs={"secret/p": SecretDiff(changed={"k": ("a", "b")}, only_in_left={}, only_in_right={})},
    )
    runner = CliRunner()
    with _patch_deps(diff_result):
        out = runner.invoke(
            compare_command,
            BASE_ARGS + ["--path", "secret/p", "--exit-code"],
        )
    assert out.exit_code == 1


def test_compare_no_exit_code_flag_exits_zero():
    diff_result = ComparisonResult(
        paths=["secret/p"],
        diffs={"secret/p": SecretDiff(changed={"k": ("a", "b")}, only_in_left={}, only_in_right={})},
    )
    runner = CliRunner()
    with _patch_deps(diff_result):
        out = runner.invoke(compare_command, BASE_ARGS + ["--path", "secret/p"])
    assert out.exit_code == 0


def test_compare_vault_client_error_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_comparator.VaultClient", side_effect=VaultClientError("bad token")):
        out = runner.invoke(compare_command, BASE_ARGS + ["--path", "secret/a"])
    assert out.exit_code == 1
    assert "Vault connection error" in out.output


def test_compare_recursive_uses_root():
    result = _clean_result(["secret/env/a"])
    runner = CliRunner()
    mock_comparator = MagicMock(
        compare=MagicMock(return_value=result),
        compare_recursive=MagicMock(return_value=result),
    )
    with patch.multiple(
        "vaultdiff.cli_comparator",
        VaultClient=MagicMock(),
        VaultDiffer=MagicMock(),
        Comparator=MagicMock(return_value=mock_comparator),
    ):
        out = runner.invoke(compare_command, BASE_ARGS + ["--recursive", "secret/env"])
    assert out.exit_code == 0
    mock_comparator.compare_recursive.assert_called_once_with("secret/env")


def test_compare_missing_path_and_recursive_shows_error():
    runner = CliRunner()
    with patch("vaultdiff.cli_comparator.VaultClient", MagicMock()):
        out = runner.invoke(compare_command, BASE_ARGS)
    assert out.exit_code != 0
