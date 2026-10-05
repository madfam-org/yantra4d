"""Persistent writable storage for user projects, end to end.

The layout under test is the container's: the commons (``PROJECTS_DIR``) is
shipped with the release and is READ-ONLY, and every user-authored cartridge
lives in a separate, writable ``USER_PROJECTS_DIR``. Both the API and the render
worker must resolve a cartridge there.

The flow is the Studio's: fork a commons cartridge, save an edit to the fork
(the SCAD autosave call), render the fork. The render goes through the real
``/api/render`` route and the real worker task handler; only the Redis hop
between them (replaced by an in-process hand-off of the JSON task) and the
OpenSCAD binary (replaced by a fake that reads the source it was given) are
stubbed, so the test needs neither service and runs in CI.
"""
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

WORKER_DIR = Path(__file__).resolve().parents[3] / "worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

SOURCE_SLUG = "commons-box"
FORK_SLUG = "my-box"
ORIGINAL_SCAD = "cube(10);\n"
EDITED_SCAD = "cube([20, 10, 5]); // edited in the fork\n"

MANIFEST = {
    "project": {
        "thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner",
        "name": "Commons Box", "slug": SOURCE_SLUG, "version": "1.0.0",
    },
    "modes": [{
        "id": "default", "scad_file": "main.scad", "label": {"en": "Default"},
        "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"},
    }],
    "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
    "parameters": [],
    "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
}


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def _make_read_only(root: Path) -> None:
    """chmod the commons tree read-only, as the image's root filesystem is."""
    for path in sorted(root.rglob("*"), reverse=True):
        mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        if path.is_dir():
            mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        path.chmod(mode)
    root.chmod(0o555)


def _make_writable(root: Path) -> None:
    root.chmod(0o755)
    for path in root.rglob("*"):
        path.chmod(0o755 if path.is_dir() else 0o644)


@pytest.fixture
def layout(tmp_path, monkeypatch, user_projects_dir):
    """A read-only commons with one cartridge, and an empty user-projects root."""
    from config import Config

    commons = tmp_path / "commons"
    cart = commons / SOURCE_SLUG
    cart.mkdir(parents=True)
    (cart / "project.json").write_text(json.dumps(MANIFEST))
    (cart / "main.scad").write_text(ORIGINAL_SCAD)

    static = tmp_path / "static"
    static.mkdir()
    monkeypatch.setattr(Config, "PROJECTS_DIR", commons)
    monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", tmp_path / "private-projects")
    monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [commons, user_projects_dir])
    monkeypatch.setattr(Config, "STATIC_DIR", static)

    _make_read_only(commons)
    yield commons, user_projects_dir, static
    # pytest must be able to clean tmp_path up afterwards.
    _make_writable(commons)


@pytest.fixture
def client(layout):
    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


@pytest.fixture
def worker_bridge(layout, monkeypatch):
    """Route /api/render's per-part jobs straight into the worker's handler.

    Stands in for the Redis queue only: the task is JSON round-tripped exactly
    as it would be through ``RPUSH``/``BLPOP``, then handed to
    ``render_worker.process_sync_task``. Returns the list of source files the
    fake OpenSCAD was asked to render, with the bytes it read from each.
    """
    import render_worker

    import services.engine.render_orchestrator as orchestrator
    from services.engine.render_cache import RenderCache
    from services.storage import FilesystemArtifactStore

    _commons, _user, static = layout
    store = FilesystemArtifactStore(static)
    monkeypatch.setattr(orchestrator, "STATIC_FOLDER", str(static))
    monkeypatch.setattr(render_worker, "STATIC_FOLDER", str(static))
    monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
    monkeypatch.setattr(render_worker, "render_cache", RenderCache(store=store))
    monkeypatch.setattr(render_worker, "_set_active_job", lambda *a, **k: None)
    monkeypatch.setattr(render_worker, "_clear_active_job", lambda *a: None)
    monkeypatch.setattr(render_worker, "_is_cancelled", lambda job_id: False)
    monkeypatch.setattr(render_worker, "stl_to_glb", lambda src, dst: False)
    monkeypatch.setattr(render_worker, "convert_mesh", lambda *a, **k: False)

    rendered: list[tuple[str, str]] = []

    def fake_openscad(cmd, scad_path=None, is_cancelled=None):
        # What a real OpenSCAD process does first: open the source it was given.
        source = Path(scad_path).read_text()
        rendered.append((scad_path, source))
        output = cmd[cmd.index("-o") + 1]
        Path(output).write_bytes(b"solid main\nendsolid main\n")
        return True, "render ok"

    monkeypatch.setattr(render_worker, "run_openscad_render", fake_openscad)
    monkeypatch.setattr(
        render_worker, "build_openscad_command",
        lambda output_path, scad_path, params, render_mode: ["openscad", "-o", output_path, scad_path],
    )

    def bridge(data, payload, engine, scad_path, actual_format, tier):
        events = []
        monkeypatch.setattr(
            render_worker, "_publish_job_event",
            lambda job_id, event, emit_final=False: events.append(event),
        )
        for i, part in enumerate(payload["parts"]):
            task = {
                "request_id": payload.get("request_id"), "mode": payload.get("mode"),
                "scad_filename": payload.get("scad_filename"), "job_id": f"job-{i}",
                "stream": False, "engine": engine, "part": part, "payload": payload,
                "scad_path": scad_path,
                "output_path": os.path.join(str(static), f"{payload['stl_prefix']}{part}.{actual_format}"),
                "export_format": payload["export_format"],
            }
            render_worker.process_sync_task(json.loads(json.dumps(task)))
        parts = [
            {k: e[k] for k in ("type", "url", "size_bytes") if k in e}
            for e in events if e.get("event") == "part_done"
        ]
        errors = [e for e in events if e.get("event") == "error"]
        assert not errors, errors
        return parts, "", (0, len(payload["parts"]))

    monkeypatch.setattr("routes.engine.render.render_parts_sync", bridge)
    return rendered


def _fork(client):
    return client.post(f"/api/projects/{SOURCE_SLUG}/fork", json={"new_slug": FORK_SLUG})


class TestForkSaveRenderWithReadOnlyCommons:
    def test_commons_is_really_read_only_here(self, layout):
        """Guards the simulation itself: the fork below must not need it."""
        commons, _user, _static = layout
        if os.geteuid() == 0:  # root ignores mode bits; the tree is still untouched below
            return
        with pytest.raises(PermissionError):
            (commons / SOURCE_SLUG / "main.scad").write_text("x")
        with pytest.raises(PermissionError):
            (commons / FORK_SLUG).mkdir()

    def test_fork_lands_in_the_user_root(self, client, layout):
        commons, user, _static = layout
        before = _snapshot(commons)

        res = _fork(client)

        assert res.status_code == 200, res.get_json()
        fork = user / FORK_SLUG
        assert (fork / "main.scad").read_text() == ORIGINAL_SCAD
        meta = json.loads((fork / "project.meta.json").read_text())
        assert meta["source"] == {"type": "fork", "forked_from": SOURCE_SLUG}
        assert not (commons / FORK_SLUG).exists()
        assert _snapshot(commons) == before

    def test_fork_then_save_then_render(self, client, layout, worker_bridge):
        commons, user, _static = layout
        before = _snapshot(commons)

        assert _fork(client).status_code == 200

        # The Studio's SCAD autosave on the fork.
        res = client.put(
            f"/api/projects/{FORK_SLUG}/files/main.scad", json={"content": EDITED_SCAD},
        )
        assert res.status_code == 200, res.get_json()
        assert (user / FORK_SLUG / "main.scad").read_text() == EDITED_SCAD

        # The editor reads it back from the user root.
        res = client.get(f"/api/projects/{FORK_SLUG}/files/main.scad")
        assert res.status_code == 200
        assert res.get_json()["content"] == EDITED_SCAD

        # Render the fork: API resolves the source, the worker renders it.
        res = client.post("/api/render", json={
            "project": FORK_SLUG, "mode": "default", "parameters": {},
        })
        assert res.status_code == 200, res.get_json()
        body = res.get_json()
        assert [p["type"] for p in body["parts"]] == ["main"]
        assert body["parts"][0]["url"].startswith(f"/static/{FORK_SLUG}_")

        # The worker read the EDITED source, from the user root.
        assert len(worker_bridge) == 1
        scad_path, source = worker_bridge[0]
        assert Path(scad_path).resolve() == (user / FORK_SLUG / "main.scad").resolve()
        assert source == EDITED_SCAD

        # The commons was never written, by any step.
        assert _snapshot(commons) == before

    def test_the_render_cache_identity_follows_the_fork_source(self, client, layout):
        """The payload hashes the fork's file, so an edit is a new render."""
        from services.engine.render_orchestrator import extract_render_payload

        _commons, user, _static = layout
        assert _fork(client).status_code == 200
        client.put(f"/api/projects/{FORK_SLUG}/files/main.scad", json={"content": EDITED_SCAD})

        with client.application.test_request_context():
            payload = extract_render_payload({"project": FORK_SLUG, "mode": "default", "parameters": {}})
        assert Path(payload["scad_path"]).resolve() == (user / FORK_SLUG / "main.scad").resolve()
        assert payload["scad_content_hash"] == hashlib.md5(EDITED_SCAD.encode()).hexdigest()


class TestSlugsAreUniqueAcrossRoots:
    def test_fork_cannot_take_a_commons_slug(self, client, layout):
        _commons, user, _static = layout
        res = client.post(f"/api/projects/{SOURCE_SLUG}/fork", json={"new_slug": SOURCE_SLUG})
        assert res.status_code == 409
        assert not (user / SOURCE_SLUG).exists()

    def test_fork_cannot_take_an_existing_fork_slug(self, client, layout):
        assert _fork(client).status_code == 200
        assert _fork(client).status_code == 409

    def test_fork_cannot_take_a_private_slug(self, client, layout, tmp_path, monkeypatch):
        from config import Config
        private = tmp_path / "private-projects"
        (private / "client-cart").mkdir(parents=True)
        monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", private)

        res = client.post(f"/api/projects/{SOURCE_SLUG}/fork", json={"new_slug": "client-cart"})
        assert res.status_code == 409

    def test_onboarding_cannot_take_a_commons_slug(self, client, layout):
        _commons, user, _static = layout
        res = client.post("/api/projects/create", json={"manifest": MANIFEST})
        assert res.status_code == 409
        assert not (user / SOURCE_SLUG).exists()

    def test_a_fork_resolves_after_curated_roots(self, client, layout):
        """Even if a user cartridge appears under a curated slug (a release
        added it later), the curated one answers."""
        _commons, user, _static = layout
        shadow = user / SOURCE_SLUG
        shadow.mkdir(parents=True)
        (shadow / "project.json").write_text(json.dumps(MANIFEST))
        (shadow / "main.scad").write_text("sphere(1); // shadowed\n")

        res = client.get(f"/api/projects/{SOURCE_SLUG}/files/main.scad")
        assert res.status_code == 200
        assert res.get_json()["content"] == ORIGINAL_SCAD
