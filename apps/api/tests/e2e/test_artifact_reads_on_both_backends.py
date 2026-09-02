"""Routes that *read* a render artifact, on both backends.

Serving `/static` was the obvious half of the object-storage change and it was
done first. This is the other half: four routes consume a rendered mesh without
ever going through `/static` — wall-thickness and overhang analysis, the FEA
stress overlay, the Cotiza quote, the design verifier — and each of them found
its mesh by globbing or joining `Config.STATIC_DIR`. Under
`RENDER_ARTIFACT_STORE=s3` that directory is scratch: the render succeeded, the
artifact is in the bucket, and every one of these routes reported "no rendered
mesh found" or "not rendered yet".

Each test runs against both backends, and asserts the same answer from both.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from config import Config
from services.storage import FilesystemArtifactStore, S3ArtifactStore, set_artifact_store

SLUG = "open-widget"
PART = "body"
#: One stored render, under the name both readers address it by: the analysis
#: routes take the newest artifact carrying the project's prefix, and the
#: verifier addresses `<slug>_<STL_PREFIX><part>.stl` exactly.
ARTIFACT = f"{SLUG}_preview_{PART}.stl"
PRINTER_ID = "printer-one"
MESH = b"solid body\nendsolid body\n"

THICKNESS = {
    "thicknesses": [1.0], "points": [[0, 0, 0]], "min": 1.0, "max": 1.0,
    "mean": 1.0, "thin_wall_count": 0, "sample_count": 1, "valid_hits": 1,
}


def _manifest() -> dict:
    return {
        "project": {
            "name": SLUG, "slug": SLUG, "version": "1.0.0",
            "thumbnail": "t.png", "tags": [], "difficulty": "beginner",
        },
        "modes": [{
            "id": "default", "scad_file": "main.scad", "label": {"en": "Default"},
            "parts": [PART], "estimate": {"base_units": 1, "formula": "constant"},
        }],
        "parts": [{"id": PART, "render_mode": 0, "label": {"en": "Body"},
                   "default_color": "#fff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 1, "per_unit": 0.1, "per_part": 0.5},
    }


@pytest.fixture
def project(tmp_path):
    project_dir = tmp_path / SLUG
    project_dir.mkdir()
    (project_dir / "project.json").write_text(json.dumps(_manifest()))
    (project_dir / "main.scad").write_text("cube(10);")
    return tmp_path


@pytest.fixture(params=["fs", "s3"])
def rendered(request, project, tmp_path, monkeypatch, fake_s3_client):
    """The app, with one render already stored, on each backend in turn."""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    monkeypatch.setattr(Config, "STATIC_DIR", static_dir)

    if request.param == "fs":
        store = FilesystemArtifactStore()
    else:
        store = S3ArtifactStore(
            bucket="renders", endpoint_url="http://object-store.test:9000",
            prefix="renders/v1", client=fake_s3_client,
        )
    monkeypatch.setattr(Config, "RENDER_ARTIFACT_STORE", request.param)
    set_artifact_store(store)
    store.put_bytes(ARTIFACT, MESH)

    from app import create_app
    application = create_app()
    application.config["TESTING"] = True
    return application.test_client(), store, static_dir


@pytest.fixture
def client(rendered):
    return rendered[0]


@pytest.fixture
def store(rendered):
    return rendered[1]


class TestAnalysisFindsTheRender:
    def test_thickness_analysis_reaches_the_stored_mesh(self, client):
        seen = []

        def fake_compute(mesh_path, **_kwargs):
            # Read it here, not afterwards: on an object store the file is a
            # temporary copy that only exists for the length of the call.
            with open(mesh_path, "rb") as fh:
                seen.append(fh.read())
            return THICKNESS

        with patch("routes.engine.analysis.compute_wall_thickness", fake_compute):
            res = client.post(f"/api/projects/{SLUG}/analyze/thickness")

        assert res.status_code == 200, res.get_json()
        body = res.get_json()
        assert body["status"] == "success"
        assert body["mesh_file"] == ARTIFACT
        # Whatever the backend, the analyzer was handed a real, readable file.
        assert seen == [MESH]

    def test_overhang_analysis_reaches_the_stored_mesh(self, client):
        with patch("routes.engine.analysis.compute_overhang_angles",
                   return_value={"angles": [], "points": []}):
            res = client.post(f"/api/projects/{SLUG}/analyze/overhang")
        assert res.status_code == 200, res.get_json()
        assert res.get_json()["mesh_file"] == ARTIFACT

    def test_an_unrendered_project_is_still_a_409(self, client, store):
        assert store.delete(ARTIFACT) is True
        res = client.post(f"/api/projects/{SLUG}/analyze/thickness")
        assert res.status_code == 409
        assert "Render first" in res.get_json()["error"]

    def test_no_downloaded_copy_is_left_behind(self, client, store, static_dir_of):
        """An object-store read is a temporary file, and temporary means gone."""
        before = {info.key for info in store.list()}
        with patch("routes.engine.analysis.compute_wall_thickness",
                   return_value=THICKNESS):
            client.post(f"/api/projects/{SLUG}/analyze/thickness")
        assert {info.key for info in store.list()} == before
        assert sorted(p.name for p in static_dir_of.iterdir()) == (
            [] if store.local_root() is None else [ARTIFACT]
        )


@pytest.fixture
def static_dir_of(rendered):
    return rendered[2]


class TestVerifyFindsTheRender:
    def _run(self, client, seen):
        """Run /api/verify with the verifier subprocess replaced by a reader.

        The mesh has to be read *while the route holds it*: on an object store
        the file is a temporary copy that is gone the moment the request ends,
        which is precisely the property being asserted.
        """
        def fake_run(cmd, **_kwargs):
            with open(cmd[2], "rb") as fh:
                seen.append(fh.read())
            result = MagicMock()
            result.stdout = 'ok\n===JSON===\n{"passed": true}'
            result.stderr = ""
            result.returncode = 0
            return result

        with patch("routes.engine.verify.subprocess.run", side_effect=fake_run):
            return client.post("/api/verify", json={"mode": "default", "project": SLUG})

    def test_a_stored_part_verifies(self, client):
        seen = []
        res = self._run(client, seen)
        assert res.status_code == 200, res.get_json()
        assert res.get_json()["passed"] is True
        # The verifier is a subprocess: it was given a path holding the mesh.
        assert seen == [MESH]

    def test_a_part_that_was_never_rendered_is_still_a_409(self, client, store):
        assert store.delete(ARTIFACT) is True
        res = self._run(client, [])
        assert res.status_code == 409
        assert res.get_json()["error"] == "not_rendered"


class TestPrinterDispatchFindsTheRender:
    def test_the_uploaded_file_is_the_stored_artifact(self, client, monkeypatch, tmp_path):
        printers_dir = tmp_path / "printers"
        printers_dir.mkdir()
        (printers_dir / f"{PRINTER_ID}.json").write_text(json.dumps({
            "id": PRINTER_ID, "name": "Test", "type": "octoprint",
            "connection": {"base_url": "http://printer.test", "api_key": "k"},
        }))
        import routes.integrations.printer as printer_mod
        monkeypatch.setattr(printer_mod, "PRINTERS_DIR", printers_dir)

        uploaded = {}

        class FakeClient:
            @staticmethod
            def upload_file(base_url, api_key, path):
                with open(path, "rb") as fh:
                    uploaded["bytes"] = fh.read()
                return "remote.stl"

            @staticmethod
            def start_print(base_url, api_key, name):
                uploaded["started"] = name

        monkeypatch.setattr(printer_mod, "_get_client", lambda printer: FakeClient)

        res = client.post(f"/api/printers/{PRINTER_ID}/print", json={"file_path": ARTIFACT})

        assert res.status_code == 200, res.get_json()
        assert uploaded["bytes"] == MESH
        assert uploaded["started"] == "remote.stl"

    def test_a_traversing_file_path_is_still_refused(self, client, monkeypatch, tmp_path):
        printers_dir = tmp_path / "printers"
        printers_dir.mkdir()
        (printers_dir / f"{PRINTER_ID}.json").write_text(json.dumps({
            "id": PRINTER_ID, "name": "Test", "type": "octoprint",
            "connection": {"base_url": "http://printer.test", "api_key": "k"},
        }))
        import routes.integrations.printer as printer_mod
        monkeypatch.setattr(printer_mod, "PRINTERS_DIR", printers_dir)

        res = client.post(f"/api/printers/{PRINTER_ID}/print", json={"file_path": "../../etc/passwd"})
        assert res.status_code == 400
