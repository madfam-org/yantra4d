"""Real Git histories exercise gitlink changes, shallow pins, and hard failures."""
import importlib.util
from pathlib import Path
import subprocess

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "ci/select_render_cartridges.py"
spec = importlib.util.spec_from_file_location("select_render_cartridges", SOURCE)
lane = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lane)


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], stderr=subprocess.PIPE).decode().strip()


def init(path):
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.name", "Fixture")
    git(path, "config", "user.email", "fixture@example.invalid")


def write(path, content="{}"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def commit(path):
    git(path, "add", ".")
    git(path, "commit", "-qm", "fixture")
    return git(path, "rev-parse", "HEAD")


def history(tmp_path, changed="alpha/main.py", shallow=False):
    origin, platform = tmp_path / "origin", tmp_path / "platform"
    init(origin)
    for slug in ["alpha", "beta"]:
        write(origin / slug / "project.json")
        write(origin / slug / "main.py", "initial")
    old = commit(origin)
    write(origin / changed, "updated")
    new = commit(origin)
    init(platform)
    clone_args = ["--depth", "1"] if shallow else []
    git(platform, "clone", "-q", *clone_args, origin.as_uri(), "projects")
    git(platform, "update-index", "--add", "--cacheinfo", f"160000,{old},projects")
    git(platform, "commit", "-qm", "old pin")
    base = git(platform, "rev-parse", "HEAD")
    git(platform, "update-index", "--cacheinfo", f"160000,{new},projects")
    git(platform, "commit", "-qm", "new pin")
    return platform, base, old


@pytest.mark.parametrize("shallow", [False, True])
def test_gitlink_change_selects_inner_cartridge(tmp_path, shallow):
    repo, base, old = history(tmp_path, shallow=shallow)
    if shallow:
        with pytest.raises(subprocess.CalledProcessError):
            git(repo / "projects", "cat-file", "-e", old)
    assert lane.select(repo, base) == [repo / "projects/alpha"]


@pytest.mark.parametrize("changed", ["libs/BOSL2/example.scad", "commons-lib/shared.scad"])
def test_shared_dependencies_select_every_cartridge(tmp_path, changed):
    repo, base, _ = history(tmp_path, changed=changed)
    assert lane.select(repo, base) == [repo / "projects/alpha", repo / "projects/beta"]


def test_commons_documentation_change_does_not_select_cartridges(tmp_path):
    repo, base, _ = history(tmp_path, changed="docs/README.md")
    assert lane.select(repo, base) == []


def test_unchanged_gitlink_is_empty(tmp_path):
    repo, _, _ = history(tmp_path)
    assert lane.select(repo, "HEAD") == []


def test_wrong_checked_out_pin_is_not_a_skip(tmp_path):
    repo, base, old = history(tmp_path)
    git(repo / "projects", "checkout", "-q", old)
    with pytest.raises(ValueError, match="does not match"):
        lane.select(repo, base)


def test_unavailable_base_history_is_not_a_skip(tmp_path):
    repo, base, _ = history(tmp_path, shallow=True)
    git(repo / "projects", "remote", "set-url", "origin", str(tmp_path / "missing"))
    with pytest.raises(subprocess.CalledProcessError):
        lane.select(repo, base)


def test_missing_platform_history_is_not_a_skip(tmp_path):
    repo, _, _ = history(tmp_path)
    with pytest.raises(subprocess.CalledProcessError):
        lane.select(repo, "0" * 40)


def test_removed_commons_cannot_use_stale_checkout(tmp_path):
    repo, base, _ = history(tmp_path)
    git(repo, "update-index", "--force-remove", "projects")
    git(repo, "commit", "-qm", "remove commons")
    with pytest.raises(ValueError, match="no commons tree"):
        lane.select(repo, base)


def test_legacy_tracked_cartridge_selection(tmp_path):
    repo = tmp_path / "legacy"
    init(repo)
    write(repo / "projects/alpha/project.json")
    write(repo / "projects/beta/project.json")
    base = commit(repo)
    write(repo / "projects/alpha/main.py", "changed")
    commit(repo)
    assert lane.select(repo, base) == [repo / "projects/alpha"]


def test_empty_checkout_is_not_a_skip(tmp_path):
    repo = tmp_path / "empty"
    init(repo)
    write(repo / "README.md")
    base = commit(repo)
    with pytest.raises(ValueError, match="No commons"):
        lane.select(repo, base)
