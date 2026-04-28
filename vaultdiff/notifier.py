"""Notification dispatch for VaultDiff audit results."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.auditor import AuditEntry


class NotifierError(Exception):
    """Raised when a notification fails to dispatch."""


@dataclass
class NotifierConfig:
    webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    only_on_differences: bool = True
    extra_headers: dict = field(default_factory=dict)


class Notifier:
    """Dispatches audit entries to a configured webhook endpoint."""

    def __init__(self, config: NotifierConfig) -> None:
        self.config = config

    def _should_send(self, entries: List[AuditEntry]) -> bool:
        if not self.config.webhook_url:
            return False
        if self.config.only_on_differences:
            return any(e.has_differences for e in entries)
        return True

    def _build_payload(self, entries: List[AuditEntry]) -> dict:
        records = [e.to_dict() for e in entries]
        payload: dict = {"vaultdiff_audit": records}
        if self.config.slack_channel:
            summary = f"VaultDiff: {sum(1 for e in entries if e.has_differences)} path(s) with differences"
            payload["text"] = summary
            payload["channel"] = self.config.slack_channel
        return payload

    def send(self, entries: List[AuditEntry]) -> None:
        """Send audit entries to the configured webhook. Raises NotifierError on failure."""
        if not self._should_send(entries):
            return

        payload = self._build_payload(entries)
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", **self.config.extra_headers}

        req = urllib.request.Request(
            self.config.webhook_url,  # type: ignore[arg-type]
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    raise NotifierError(f"Webhook returned HTTP {resp.status}")
        except NotifierError:
            raise
        except Exception as exc:
            raise NotifierError(f"Failed to send notification: {exc}") from exc
