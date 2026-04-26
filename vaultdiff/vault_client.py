"""Vault client wrapper for reading secrets from HashiCorp Vault."""

import os
from typing import Optional

import hvac


class VaultClientError(Exception):
    """Raised when a Vault operation fails."""


class VaultClient:
    """Thin wrapper around hvac.Client for reading KV secrets."""

    def __init__(self, url: str, token: Optional[str] = None, namespace: Optional[str] = None):
        self.url = url
        self.token = token or os.environ.get("VAULT_TOKEN")
        self.namespace = namespace or os.environ.get("VAULT_NAMESPACE")

        if not self.token:
            raise VaultClientError(
                "Vault token must be provided via argument or VAULT_TOKEN env var."
            )

        self._client = hvac.Client(
            url=self.url,
            token=self.token,
            namespace=self.namespace,
        )

        if not self._client.is_authenticated():
            raise VaultClientError(f"Failed to authenticate with Vault at {self.url}")

    def read_secret(self, path: str, mount_point: str = "secret") -> dict:
        """Read a KV v2 secret and return its data dict."""
        try:
            response = self._client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=mount_point,
            )
            return response["data"]["data"]
        except hvac.exceptions.InvalidPath:
            raise VaultClientError(f"Secret path not found: {mount_point}/{path}")
        except hvac.exceptions.Forbidden:
            raise VaultClientError(f"Permission denied reading: {mount_point}/{path}")
        except Exception as exc:
            raise VaultClientError(f"Unexpected error reading secret: {exc}") from exc

    def list_secrets(self, path: str, mount_point: str = "secret") -> list[str]:
        """List keys under a KV v2 path."""
        try:
            response = self._client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=mount_point,
            )
            return response["data"]["keys"]
        except hvac.exceptions.InvalidPath:
            raise VaultClientError(f"Path not found or empty: {mount_point}/{path}")
        except hvac.exceptions.Forbidden:
            raise VaultClientError(f"Permission denied listing: {mount_point}/{path}")
        except Exception as exc:
            raise VaultClientError(f"Unexpected error listing secrets: {exc}") from exc
