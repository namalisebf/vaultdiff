"""Tests for vaultdiff.blender."""
from vaultdiff.differ import SecretDiff
from vaultdiff.blender import BlendedPath, BlendReport, blend_diffs


def _diff(path, changed=None, only_left=None, only_right=None):
    return SecretDiff(
        path=path,
        changed_keys=changed or {},
        only_in_left=only_left or {},
        only_in_right=only_right or {},
    )


def test_blend_empty_input_returns_empty_report():
    report = blend_diffs({})
    assert report.total_paths == 0
    assert report.dirty_paths == 0
    assert report.entries == []


def test_blend_single_env_clean_diff():
    report = blend_diffs({"prod": [_diff("secret/app")]})
    assert report.total_paths == 1
    assert report.dirty_paths == 0
    entry = report.entries[0]
    assert entry.path == "secret/app"
    assert entry.envs == ["prod"]
    assert not entry.has_differences()


def test_blend_single_env_changed_key():
    report = blend_diffs({
        "staging": [_diff("secret/db", changed={"password": ("old", "new")})]
    })
    entry = report.entries[0]
    assert entry.has_differences()
    assert "password" in entry.changed_keys
    assert entry.changed_keys["password"] == ["staging"]


def test_blend_two_envs_same_path_accumulates_envs():
    report = blend_diffs({
        "prod": [_diff("secret/app", changed={"key": ("a", "b")})],
        "staging": [_diff("secret/app", changed={"key": ("x", "y")})],
    })
    assert report.total_paths == 1
    entry = report.entries[0]
    assert set(entry.envs) == {"prod", "staging"}
    assert set(entry.changed_keys["key"]) == {"prod", "staging"}


def test_blend_two_envs_different_paths():
    report = blend_diffs({
        "prod": [_diff("secret/a")],
        "staging": [_diff("secret/b")],
    })
    assert report.total_paths == 2
    paths = {e.path for e in report.entries}
    assert paths == {"secret/a", "secret/b"}


def test_blend_only_in_left_tracked_per_env():
    report = blend_diffs({
        "prod": [_diff("secret/x", only_left={"gone_key": "val"})],
    })
    entry = report.entries[0]
    assert "gone_key" in entry.only_in_left
    assert entry.only_in_left["gone_key"] == ["prod"]


def test_blend_only_in_right_tracked_per_env():
    report = blend_diffs({
        "prod": [_diff("secret/x", only_right={"new_key": "val"})],
    })
    entry = report.entries[0]
    assert "new_key" in entry.only_in_right
    assert entry.only_in_right["new_key"] == ["prod"]


def test_blend_dirty_paths_count():
    report = blend_diffs({
        "prod": [
            _diff("secret/clean"),
            _diff("secret/dirty", changed={"k": ("a", "b")}),
        ]
    })
    assert report.dirty_paths == 1


def test_blend_to_dict_structure():
    report = blend_diffs({"prod": [_diff("secret/app")]})
    d = report.to_dict()
    assert "total_paths" in d
    assert "dirty_paths" in d
    assert "entries" in d
    assert isinstance(d["entries"], list)
    entry_dict = d["entries"][0]
    assert "path" in entry_dict
    assert "envs" in entry_dict
    assert "has_differences" in entry_dict
