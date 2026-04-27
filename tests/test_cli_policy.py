"""Integration-style tests for the policy-check CLI command."""
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from vaultdiff.cli_policy import policy_check_command
from vaultdiff.differ import SecretDiff
from vaultdiff.policy import PolicyViolation
from vaultdiff.vault_client import VaultClientError


_BASE_ARGS = [
    "--path", "secret/app",
    "--addr-left", "http://left:8200",
    "--addr-right", "http://right:8200",
    "--token-left", "tok-l",
    "--token-right", "tok-r",
]


def _no_violations_diff():
    return SecretDiff(
        path="secret/app",
        changed_keys=[],
        only_in_left=[],
        only_in_right=[],
        left_data={},
        right_data={},
    )


def _patch_deps(diff=None, client_error=None):
    mock_client = MagicMock()
    mock_differ = MagicMock()
    if client_error:
        mock_differ.diff_secret.side_effect = client_error
    else:
        mock_differ.diff_secret.return_value = diff or _no_violations_diff()

    patches = [
        patch("vaultdiff.cli_policy.VaultClient", return_value=mock_client),
        patch("vaultdiff.cli_policy.VaultDiffer", return_value=mock_differ),
    ]
    return patches


def test_policy_check_no_violations():
    runner = CliRunner()
    with patch("vaultdiff.cli_policy.VaultClient"), \
         patch("vaultdiff.cli_policy.VaultDiffer") as mock_differ_cls:
        mock_differ_cls.return_value.diff_secret.return_value = _no_violations_diff()
        result = runner.invoke(policy_check_command, _BASE_ARGS)
    assert result.exit_code == 0
    assert "No policy violations found" in result.output


def test_policy_check_detects_violation():
    runner = CliRunner()
    diff = SecretDiff(
        path="secret/app",
        changed_keys=[],
        only_in_left=[],
        only_in_right=["bad-key"],
        left_data={},
        right_data={"bad-key": "val"},
    )
    with patch("vaultdiff.cli_policy.VaultClient"), \
         patch("vaultdiff.cli_policy.VaultDiffer") as mock_differ_cls:
        mock_differ_cls.return_value.diff_secret.return_value = diff
        result = runner.invoke(
            policy_check_command,
            _BASE_ARGS + ["--required-key-pattern", r"^[A-Z_]+$"],
        )
    assert "required_key_pattern" in result.output


def test_policy_check_exit_code_on_violations():
    runner = CliRunner()
    diff = SecretDiff(
        path="secret/app",
        changed_keys=[],
        only_in_left=[],
        only_in_right=["bad-key"],
        left_data={},
        right_data={"bad-key": ""},
    )
    with patch("vaultdiff.cli_policy.VaultClient"), \
         patch("vaultdiff.cli_policy.VaultDiffer") as mock_differ_cls:
        mock_differ_cls.return_value.diff_secret.return_value = diff
        result = runner.invoke(
            policy_check_command,
            _BASE_ARGS + ["--disallow-empty", "--exit-code"],
        )
    assert result.exit_code == 2


def test_policy_check_json_output():
    runner = CliRunner()
    with patch("vaultdiff.cli_policy.VaultClient"), \
         patch("vaultdiff.cli_policy.VaultDiffer") as mock_differ_cls:
        mock_differ_cls.return_value.diff_secret.return_value = _no_violations_diff()
        result = runner.invoke(
            policy_check_command, _BASE_ARGS + ["--output", "json"]
        )
    assert result.exit_code == 0
    assert result.output.strip().startswith("[")


def test_policy_check_vault_error_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_policy.VaultClient"), \
         patch("vaultdiff.cli_policy.VaultDiffer") as mock_differ_cls:
        mock_differ_cls.return_value.diff_secret.side_effect = VaultClientError("boom")
        result = runner.invoke(policy_check_command, _BASE_ARGS)
    assert result.exit_code == 1
