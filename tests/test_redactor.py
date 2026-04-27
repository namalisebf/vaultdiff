"""Tests for vaultdiff.redactor."""

import pytest
from vaultdiff.redactor import Redactor, RedactorConfig, DEFAULT_MASK


def _redactor(**kwargs) -> Redactor:
    return Redactor(RedactorConfig(**kwargs))


def test_is_sensitive_default_patterns():
    r = Redactor()
    assert r.is_sensitive("db_password") is True
    assert r.is_sensitive("api_key") is True
    assert r.is_sensitive("auth_token") is True
    assert r.is_sensitive("private_key") is True
    assert r.is_sensitive("aws_secret") is True


def test_is_sensitive_non_sensitive_key():
    r = Redactor()
    assert r.is_sensitive("database_host") is False
    assert r.is_sensitive("port") is False
    assert r.is_sensitive("region") is False


def test_redact_value_masks_sensitive():
    r = Redactor()
    result = r.redact_value("db_password", "s3cr3t")
    assert result == DEFAULT_MASK


def test_redact_value_preserves_non_sensitive():
    r = Redactor()
    result = r.redact_value("database_host", "localhost")
    assert result == "localhost"


def test_redact_dict_mixed_keys():
    r = Redactor()
    data = {"host": "localhost", "password": "hunter2", "port": "5432"}
    result = r.redact_dict(data)
    assert result["host"] == "localhost"
    assert result["password"] == DEFAULT_MASK
    assert result["port"] == "5432"


def test_redactor_disabled_skips_all_masking():
    r = _redactor(enabled=False)
    assert r.is_sensitive("password") is False
    assert r.redact_value("password", "s3cr3t") == "s3cr3t"


def test_custom_mask():
    r = _redactor(mask="<hidden>")
    assert r.redact_value("api_key", "abc123") == "<hidden>"


def test_additional_patterns():
    r = _redactor(additional_patterns=[r"(?i)ssn", r"(?i)credit_card"])
    assert r.is_sensitive("user_ssn") is True
    assert r.is_sensitive("credit_card_number") is True
    assert r.is_sensitive("username") is False


def test_redact_dict_returns_copy():
    r = Redactor()
    original = {"host": "localhost", "token": "abc"}
    result = r.redact_dict(original)
    assert original["token"] == "abc"  # original unchanged
    assert result["token"] == DEFAULT_MASK
