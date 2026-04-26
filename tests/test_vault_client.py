"""Unit tests for vaultdiff.vault_client."""

from unittest.mock import MagicMock, patch

import pytest

from vaultdiff.vault_client import VaultClient, VaultClientError


AUTHENTICATED_PATCH = "vaultdiff.vault_client.hvac.Client"


def _make_mock_hvac(authenticated: bool = True):
    mock_hvac = MagicMock()
    mock_hvac.return_value.is_authenticated.return_value = authenticated
    return mock_hvac


def test_init_raises_without_token():
    with patch("vaultdiff.vault_client.os.environ.get", return_value=None):
        with pytest.raises(VaultClientError, match="Vault token"):
            VaultClient(url="http://localhost:8200")


def test_init_raises_when_not_authenticated():
    mock_hvac = _make_mock_hvac(authenticated=False)
    with patch(AUTHENTICATED_PATCH, mock_hvac):
        with pytest.raises(VaultClientError, match="Failed to authenticate"):
            VaultClient(url="http://localhost:8200", token="bad-token")


def test_read_secret_returns_data():
    mock_hvac = _make_mock_hvac()
    mock_hvac.return_value.secrets.kv.v2.read_secret_version.return_value = {
        "data": {"data": {"api_key": "abc123", "db_pass": "secret"}}
    }
    with patch(AUTHENTICATED_PATCH, mock_hvac):
        client = VaultClient(url="http://localhost:8200", token="root")
        result = client.read_secret("myapp/config")

    assert result == {"api_key": "abc123", "db_pass": "secret"}


def test_read_secret_raises_on_invalid_path():
    import hvac.exceptions

    mock_hvac = _make_mock_hvac()
    mock_hvac.return_value.secrets.kv.v2.read_secret_version.side_effect = (
        hvac.exceptions.InvalidPath()
    )
    with patch(AUTHENTICATED_PATCH, mock_hvac):
        client = VaultClient(url="http://localhost:8200", token="root")
        with pytest.raises(VaultClientError, match="not found"):
            client.read_secret("missing/path")


def test_list_secrets_returns_keys():
    mock_hvac = _make_mock_hvac()
    mock_hvac.return_value.secrets.kv.v2.list_secrets.return_value = {
        "data": {"keys": ["config", "credentials"]}
    }
    with patch(AUTHENTICATED_PATCH, mock_hvac):
        client = VaultClient(url="http://localhost:8200", token="root")
        result = client.list_secrets("myapp")

    assert result == ["config", "credentials"]


def test_list_secrets_raises_on_forbidden():
    import hvac.exceptions

    mock_hvac = _make_mock_hvac()
    mock_hvac.return_value.secrets.kv.v2.list_secrets.side_effect = (
        hvac.exceptions.Forbidden()
    )
    with patch(AUTHENTICATED_PATCH, mock_hvac):
        client = VaultClient(url="http://localhost:8200", token="root")
        with pytest.raises(VaultClientError, match="Permission denied"):
            client.list_secrets("restricted")
