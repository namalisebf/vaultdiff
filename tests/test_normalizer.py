"""Tests for vaultdiff.normalizer."""
import pytest
from vaultdiff.normalizer import Normalizer, NormalizerConfig, NormalizedSecret


def _make_normalizer(**kwargs) -> Normalizer:
    return Normalizer(NormalizerConfig(**kwargs))


def test_normalize_value_strips_whitespace():
    n = _make_normalizer(strip_whitespace=True)
    assert n.normalize_value("key", "  hello  ") == "hello"


def test_normalize_value_no_strip_when_disabled():
    n = _make_normalizer(strip_whitespace=False)
    assert n.normalize_value("key", "  hello  ") == "  hello  "


def test_normalize_value_non_string_unchanged():
    n = _make_normalizer()
    assert n.normalize_value("key", 42) == 42
    assert n.normalize_value("key", None) is None


def test_normalize_value_replace_rule_applied():
    n = _make_normalizer(replace_rules={r"https://old\.example\.com": "https://new.example.com"})
    result = n.normalize_value("url", "https://old.example.com/path")
    assert result == "https://new.example.com/path"


def test_normalize_value_redact_pattern_masks_sensitive_key():
    n = _make_normalizer(redact_patterns=[r"password"])
    assert n.normalize_value("db_password", "s3cr3t") == "***REDACTED***"


def test_normalize_value_redact_does_not_mask_non_matching_key():
    n = _make_normalizer(redact_patterns=[r"password"])
    assert n.normalize_value("db_host", "localhost") == "localhost"


def test_normalize_secret_returns_normalized_secret_instance():
    n = _make_normalizer()
    result = n.normalize_secret("secret/app", {"key": "  val  "})
    assert isinstance(result, NormalizedSecret)
    assert result.path == "secret/app"
    assert result.normalized["key"] == "val"


def test_normalize_secret_lowercase_keys():
    n = _make_normalizer(lowercase_keys=True)
    result = n.normalize_secret("secret/app", {"MyKey": "value", "UPPER": "x"})
    assert "mykey" in result.normalized
    assert "upper" in result.normalized


def test_normalize_secret_changed_keys_detects_stripped_value():
    n = _make_normalizer(strip_whitespace=True)
    result = n.normalize_secret("secret/app", {"k": "  v  ", "clean": "ok"})
    assert "k" in result.changed_keys()
    assert "clean" not in result.changed_keys()


def test_normalize_secret_to_dict_structure():
    n = _make_normalizer()
    result = n.normalize_secret("secret/app", {"a": " 1 "})
    d = result.to_dict()
    assert d["path"] == "secret/app"
    assert "original" in d
    assert "normalized" in d
    assert "changed_keys" in d


def test_normalize_many_returns_list_for_each_path():
    n = _make_normalizer()
    secrets = {
        "secret/a": {"k": "v"},
        "secret/b": {"x": "y"},
    }
    results = n.normalize_many(secrets)
    assert len(results) == 2
    paths = {r.path for r in results}
    assert paths == {"secret/a", "secret/b"}


def test_normalizer_config_from_dict():
    cfg = NormalizerConfig.from_dict({
        "strip_whitespace": False,
        "lowercase_keys": True,
        "redact_patterns": ["secret"],
        "replace_rules": {"old": "new"},
    })
    assert cfg.strip_whitespace is False
    assert cfg.lowercase_keys is True
    assert cfg.redact_patterns == ["secret"]
    assert cfg.replace_rules == {"old": "new"}


def test_normalizer_config_from_dict_defaults():
    cfg = NormalizerConfig.from_dict({})
    assert cfg.strip_whitespace is True
    assert cfg.lowercase_keys is False
    assert cfg.redact_patterns == []
    assert cfg.replace_rules == {}
