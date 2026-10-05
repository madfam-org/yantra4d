"""The render worker's `source` and `cache_write` task fields (see worker_dispatch).

A `git_head` task renders the cartridge's committed tree from a private,
per-job checkout that the worker creates and removes itself.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

WORKER_DIR = Path(__file__).resolve().parents[3] / "worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

import render_worker

requires_git = pytest.mark.skipif(shutil.which("git") is None, reason="needs the git binary")

SLUG = "head-cart"


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


@pytest.fixture
def cartridge(tmp_path):
    """A committed cartridge at <PROJECTS_DIR>/head-cart (conftest points PROJECTS_DIR at tmp_path)."""
    project = tmp_path / SLUG
    project.mkdir()
    (project / "main.scad").write_text("cube(1); // committed")
    _git(project, "init", "-q")
    _git(project, "add", ".")
    _git(project, "commit", "-q", "-m", "init")
    (project / "main.scad").write_text("sphere(1); // working tree")
    return project


@pytest.fixture
def worker(monkeypatch, tmp_path):
    """The worker with Redis and the engines stubbed; records what happened."""
    staging = tmp_path / "static"
    staging.mkdir()
    from config import Config
    monkeypatch.setattr(Config, "STATIC_DIR", staging)
    monkeypatch.setattr(render_worker, "STATIC_FOLDER", str(staging))
    published, renders, cache_puts = [], [], []
    monkeypatch.setattr(render_worker, "_publish_job_event",
                        lambda job_id, payload, emit_final=False: published.append(payload))
    monkeypatch.setattr(render_worker, "_set_active_job", lambda *a, **k: None)
    monkeypatch.setattr(render_worker, "_clear_active_job", lambda *a: None)
    monkeypatch.setattr(render_worker, "_is_cancelled", lambda job_id: False)
    monkeypatch.setattr(render_worker, "get_manifest", lambda slug: None)
    monkeypatch.setattr(render_worker, "build_openscad_command",
                        lambda out, scad, params, mode: ["openscad", out, scad])
    monkeypatch.setattr(render_worker, "stl_to_glb", lambda src, dst: False)
    monkeypatch.setattr(render_worker.render_cache, "put", lambda *a, **k: cache_puts.append(a))

    def run(cmd, scad_path=None, is_cancelled=None):
        renders.append({"scad_path": scad_path, "content": Path(scad_path).read_text()})
        if worker.fail:
            raise RuntimeError(worker.fail)
        Path(cmd[1]).write_bytes(b"solid x\nendsolid x\n")
        return True, "ok"

    monkeypatch.setattr(render_worker, "run_openscad_render", run)
    worker.fail = None
    worker.published, worker.renders, worker.cache_puts = published, renders, cache_puts
    worker.staging = staging
    return worker


def _task(staging, *, source=None, cache_write=None, stream=False):
    payload = {"project_slug": SLUG, "params": {}, "mode_map": {}, "stl_prefix": "p_",
               "scad_filename": "main.scad", "render_revision": render_worker.render_revision()}
    if cache_write is not None:
        payload["cache_write"] = cache_write
    task = {"job_id": "job-1", "engine": "openscad", "part": "main", "payload": payload,
            "scad_path": "main.scad", "output_path": str(staging / "p_main.stl"),
            "export_format": "stl", "stream": stream}
    if source is not None:
        task["source"] = source
    if stream:
        task.update(part_index=0, num_parts=1, part_base=0, part_weight=100)
    return task


@requires_git
class TestGitHeadSource:
    def test_renders_the_committed_file_from_a_private_checkout(self, cartridge, worker):
        render_worker.process_sync_task(_task(worker.staging, source={"kind": "git_head", "entry": "main.scad"}))
        (render,) = worker.renders
        assert render["content"] == "cube(1); // committed"
        checkout = Path(render["scad_path"]).parent
        assert checkout.name.startswith("yantra_head_")
        assert not checkout.exists()  # removed when the job ended
        assert worker.published[-1]["event"] == "part_done"

    def test_checkout_is_removed_when_the_render_raises(self, cartridge, worker):
        worker.fail = "kernel exploded"
        render_worker.process_sync_task(_task(worker.staging, source={"kind": "git_head", "entry": "main.scad"}))
        assert worker.published[-1]["event"] == "error"
        assert not Path(worker.renders[0]["scad_path"]).parent.exists()

    @pytest.mark.parametrize("entry", ["../head-cart/main.scad", "/etc/hosts", "", "."])
    def test_entry_outside_the_checkout_is_refused(self, cartridge, worker, entry):
        render_worker.process_sync_task(_task(worker.staging, source={"kind": "git_head", "entry": entry}))
        assert worker.renders == []
        event = worker.published[-1]
        assert event["event"] == "error"
        assert event["source_error"] == "outside"

    def test_committed_symlink_out_of_the_tree_is_refused(self, cartridge, worker, tmp_path):
        secret = tmp_path / "outside.scad"
        secret.write_text("not yours")
        (cartridge / "link.scad").symlink_to(secret)
        _git(cartridge, "add", "link.scad")
        _git(cartridge, "commit", "-q", "-m", "link")
        render_worker.process_sync_task(_task(worker.staging, source={"kind": "git_head", "entry": "link.scad"}))
        assert worker.renders == []
        assert worker.published[-1]["source_error"] == "outside"

    def test_file_missing_from_head(self, cartridge, worker):
        (cartridge / "new.scad").write_text("cube(2);")  # never committed
        render_worker.process_sync_task(_task(worker.staging, source={"kind": "git_head", "entry": "new.scad"}))
        assert worker.renders == []
        assert worker.published[-1]["source_error"] == "missing"
        assert "does not exist in HEAD" in worker.published[-1]["error"]

    def test_project_without_git_is_unavailable(self, worker, tmp_path):
        (tmp_path / SLUG).mkdir()
        render_worker.process_sync_task(_task(worker.staging, source={"kind": "git_head", "entry": "main.scad"}))
        assert worker.renders == []
        assert worker.published[-1]["source_error"] == "unavailable"


class TestSourceAndCacheFields:
    def test_unknown_source_kind_is_an_error_not_a_render(self, worker):
        render_worker.process_sync_task(_task(worker.staging, source={"kind": "s3"}))
        assert worker.renders == []
        assert "Unsupported render source" in worker.published[-1]["error"]

    def test_stream_tasks_do_not_take_a_source(self, worker):
        render_worker.process_stream_task(_task(worker.staging, source={"kind": "git_head", "entry": "main.scad"},
                                                stream=True))
        assert worker.renders == []
        assert worker.published[-1]["event"] == "error"

    def test_cache_write_false_skips_the_render_cache(self, worker, tmp_path):
        (tmp_path / SLUG).mkdir()
        (tmp_path / SLUG / "main.scad").write_text("cube(1);")
        task = _task(worker.staging, cache_write=False)
        task["scad_path"] = str(tmp_path / SLUG / "main.scad")
        render_worker.process_sync_task(task)
        assert worker.published[-1]["event"] == "part_done"
        assert worker.cache_puts == []

    def test_cache_write_defaults_on(self, worker, tmp_path):
        (tmp_path / SLUG).mkdir()
        (tmp_path / SLUG / "main.scad").write_text("cube(1);")
        task = _task(worker.staging)
        task["scad_path"] = str(tmp_path / SLUG / "main.scad")
        render_worker.process_sync_task(task)
        assert len(worker.cache_puts) == 1
        assert json.dumps(worker.published[-1])  # serialisable event
