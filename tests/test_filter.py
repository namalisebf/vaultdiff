"""Tests for vaultdiff.filter module."""
import pytest
from vaultdiff.filter import FilterConfig


# ---------------------------------------------------------------------------
# path_allowed
# ---------------------------------------------------------------------------

def test_path_allowed_no_rules():
    cfg = FilterConfig()
    assert cfg.path_allowed("secret/prod/db") is True


def test_path_allowed_include_glob():
    cfg = FilterConfig(include_paths=["secret/prod/*"])
    assert cfg.path_allowed("secret/prod/db") is True
    assert cfg.path_allowed("secret/staging/db") is False


def test_path_allowed_exclude_glob():
    cfg = FilterConfig(exclude_paths=["secret/*/temp"])
    assert cfg.path_allowed("secret/prod/temp") is False
    assert cfg.path_allowed("secret/prod/db") is True


def test_path_allowed_include_and_exclude():
    cfg = FilterConfig(
        include_paths=["secret/prod/*"],
        exclude_paths=["secret/prod/scratch"],
    )
    assert cfg.path_allowed("secret/prod/db") is True
    assert cfg.path_allowed("secret/prod/scratch") is False
    assert cfg.path_allowed("secret/staging/db") is False


def test_path_allowed_regex_mode():
    cfg = FilterConfig(include_paths=[r"secret/(prod|staging)/"], regex=True)
    assert cfg.path_allowed("secret/prod/db") is True
    assert cfg.path_allowed("secret/staging/db") is True
    assert cfg.path_allowed("secret/dev/db") is False


# ---------------------------------------------------------------------------
# key_allowed
# ---------------------------------------------------------------------------

def test_key_allowed_no_rules():
    cfg = FilterConfig()
    assert cfg.key_allowed("password") is True


def test_key_allowed_include_glob():
    cfg = FilterConfig(include_keys=["db_*"])
    assert cfg.key_allowed("db_password") is True
    assert cfg.key_allowed("api_key") is False


def test_key_allowed_exclude_glob():
    cfg = FilterConfig(exclude_keys=["*secret*", "*password*"])
    assert cfg.key_allowed("db_password") is False
    assert cfg.key_allowed("db_host") is True


def test_key_allowed_regex_mode():
    cfg = FilterConfig(exclude_keys=[r"pass(word|phrase)"], regex=True)
    assert cfg.key_allowed("password") is False
    assert cfg.key_allowed("passphrase") is False
    assert cfg.key_allowed("token") is True


# ---------------------------------------------------------------------------
# filter_paths / filter_keys helpers
# ---------------------------------------------------------------------------

def test_filter_paths_returns_subset():
    cfg = FilterConfig(include_paths=["secret/prod/*"])
    paths = ["secret/prod/db", "secret/staging/db", "secret/prod/cache"]
    assert cfg.filter_paths(paths) == ["secret/prod/db", "secret/prod/cache"]


def test_filter_keys_returns_subset():
    cfg = FilterConfig(exclude_keys=["password"])
    keys = ["username", "password", "host"]
    assert cfg.filter_keys(keys) == ["username", "host"]
