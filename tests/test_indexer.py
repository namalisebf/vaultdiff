"""Tests for vaultdiff.indexer."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.indexer import IndexEntry, SecretIndex, build_index, _fingerprint


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _diff(
    path: str = "secret/app",
    changed: dict | None = None,
    only_left: dict | None = None,
    only_right: dict | None = None,
) -> SecretDiff:
    from vaultdiff.differ import KeyChange

    return SecretDiff(
        path=path,
        changed={k: KeyChange(left=v[0], right=v[1]) for k, v in (changed or {}).items()},
        only_in_left=only_left or {},
        only_in_right=only_right or {},
    )


# ---------------------------------------------------------------------------
# _fingerprint
# ---------------------------------------------------------------------------

def test_fingerprint_is_12_chars():
    assert len(_fingerprint("hello")) == 12


def test_fingerprint_same_value_same_hash():
    assert _fingerprint("abc") == _fingerprint("abc")


def test_fingerprint_different_values_differ():
    assert _fingerprint("abc") != _fingerprint("xyz")


# ---------------------------------------------------------------------------
# build_index
# ---------------------------------------------------------------------------

def test_build_index_empty_diffs():
    idx = build_index([])
    assert idx.entries == []


def test_build_index_invalid_side_raises():
    with pytest.raises(ValueError, match="side must be"):
        build_index([], side="both")


def test_build_index_captures_all_keys():
    d = _diff(
        changed={"DB_HOST": ("a", "b")},
        only_left={"LEFT_ONLY": "x"},
        only_right={"RIGHT_ONLY": "y"},
    )
    idx = build_index([d])
    assert len(idx.entries) == 1
    entry = idx.entries[0]
    assert set(entry.keys) == {"DB_HOST", "LEFT_ONLY", "RIGHT_ONLY"}


def test_build_index_left_side_fingerprints_left_value():
    d = _diff(changed={"API_KEY": ("secret1", "secret2")})
    idx = build_index([d], side="left")
    expected = _fingerprint("secret1")
    assert idx.entries[0].fingerprints["API_KEY"] == expected


def test_build_index_right_side_fingerprints_right_value():
    d = _diff(changed={"API_KEY": ("secret1", "secret2")})
    idx = build_index([d], side="right")
    expected = _fingerprint("secret2")
    assert idx.entries[0].fingerprints["API_KEY"] == expected


def test_build_index_only_left_key_fingerprinted_on_left_side():
    d = _diff(only_left={"TOKEN": "tok123"})
    idx = build_index([d], side="left")
    assert "TOKEN" in idx.entries[0].fingerprints


def test_build_index_only_left_key_not_fingerprinted_on_right_side():
    d = _diff(only_left={"TOKEN": "tok123"})
    idx = build_index([d], side="right")
    assert "TOKEN" not in idx.entries[0].fingerprints


# ---------------------------------------------------------------------------
# SecretIndex lookups
# ---------------------------------------------------------------------------

def test_paths_with_key_returns_matching_paths():
    d1 = _diff(path="secret/a", changed={"HOST": ("h1", "h2")})
    d2 = _diff(path="secret/b", only_left={"PORT": "5432"})
    idx = build_index([d1, d2])
    assert idx.paths_with_key("HOST") == ["secret/a"]
    assert idx.paths_with_key("PORT") == ["secret/b"]
    assert idx.paths_with_key("MISSING") == []


def test_paths_with_fingerprint_matches_correctly():
    d1 = _diff(path="secret/a", changed={"PW": ("same", "other")})
    d2 = _diff(path="secret/b", changed={"PW": ("same", "diff")})
    idx = build_index([d1, d2], side="left")
    fp = _fingerprint("same")
    result = idx.paths_with_fingerprint("PW", fp)
    assert set(result) == {"secret/a", "secret/b"}


def test_to_dict_structure():
    d = _diff(path="secret/x", changed={"K": ("v1", "v2")})
    idx = build_index([d])
    out = idx.to_dict()
    assert "entries" in out
    assert out["entries"][0]["path"] == "secret/x"
    assert "keys" in out["entries"][0]
    assert "fingerprints" in out["entries"][0]
