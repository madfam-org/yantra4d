"""Archive identity, completeness and real GLB frame contracts.

The fake native producer isolates orchestration tests; the GLB round-trip uses
trimesh's real serializer. A separately generated native archive is manual smoke
coverage, not implied by these unit tests. No API or production endpoint is used.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("render_commons_presets", REPO / "scripts/dev/render_commons_presets.py")
archive = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = archive
SPEC.loader.exec_module(archive)


def _git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def frozen(tmp_path):
    root = tmp_path / "commons"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Archive Test")
    _git(root, "config", "user.email", "archive-test@example.invalid")
    _git(root, "remote", "add", "origin", archive.COMMONS_REPOSITORY + ".git")
    folder = root / "widget"
    (folder / "docs/projections").mkdir(parents=True)
    manifest = {
        "project": {"slug": "widget", "engine": "cadquery"},
        "modes": [{"id": "assembly", "scad_file": "main.py", "parts": ["body", "closure"]},
                  {"id": "envelope", "scad_file": "main.py", "parts": ["body"]}],
        "parts": [{"id": "body", "color": "#112233"}, {"id": "closure"}],
        "parameters": [
            {"id": "width", "type": "slider", "default": 100, "min": 10, "max": 200},
            {"id": "style", "type": "select", "default": 2, "options": [{"value": 1}, {"value": 2}]},
            {"id": "lid", "type": "checkbox", "default": True}],
        "presets": [{"slug": "small", "kind": "archetype", "values": {"width": 50, "style": "1"}},
                    {"slug": "large", "mode": "envelope", "values": {"width": 150}},
                    {"slug": "folded", "kind": "fold_state", "values": {"width": 80}}],
    }
    (folder / "project.json").write_text(json.dumps(manifest))
    (folder / "main.py").write_text("# synthetic trusted source fixture\n")
    (folder / "docs/projections/small-front.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"/>')
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "frozen fixture")
    return root, _git(root, "rev-parse", "HEAD"), manifest


@pytest.fixture
def runtime():
    result = {"files": [], "versions": {"test": "unit fixture"}}
    result["fingerprint"] = archive.digest(result)
    return result


@pytest.fixture
def producer(monkeypatch):
    trimesh = pytest.importorskip("trimesh")
    calls = []

    def native(script, output, params, part, runtime_env=None):
        # build_archive must evaluate a git snapshot, not the mutable source tree.
        assert script.is_file()
        assert not (script.parent.parent / ".git").exists()
        assert runtime_env["PYTHONPATH"] == str(script.parent.parent)
        calls.append((part, dict(params)))
        mesh = trimesh.creation.box(extents=[params["width"], 20, 10])
        output.write_bytes(mesh.export(file_type="stl"))
        return True, ""

    def raster(_meshes, _camera, out, _format):
        out.write_bytes(b"synthetic-webp-producer")

    monkeypatch.setattr(archive, "native_helpers", lambda: SimpleNamespace(
        run_cadquery_part=native, load_mesh=lambda p: trimesh.load(p, force="mesh"),
        hex_to_rgb=lambda _c, _i: (0.2, 0.3, 0.4), iso_camera=lambda _m: [1, 1, 1],
        rasterize=raster,
    ))
    return calls


def test_full_pin_and_clean_source_are_required(frozen):
    root, pin, _ = frozen
    archive.verify_source(root, pin)
    with pytest.raises(archive.ArchiveError, match="full.*40"):
        archive.verify_source(root, pin[:12])
    with pytest.raises(archive.ArchiveError, match="mismatch"):
        archive.verify_source(root, "a" * 40)
    (root / "widget/main.py").write_text("# edited\n")
    with pytest.raises(archive.ArchiveError, match="dirty"):
        archive.verify_source(root, pin)


def test_preset_parameters_modes_and_fold_state_coverage(frozen):
    root, _, _ = frozen
    items, skipped = archive.preset_items(root, "widget")
    assert [x["preset"] for x in items] == ["archetype-default", "small", "large"]
    assert skipped == ["solid/widget/folded"]
    assert items[1]["requested"] == {"width": 50, "style": "1"}
    assert items[1]["resolved_parameters"] == {"width": 50.0, "style": 1, "lid": 1}
    assert isinstance(items[1]["resolved_parameters"]["style"], int)
    assert items[2]["mode"] == "envelope"
    assert items[2]["parts"] == ["body"]
    with pytest.raises(archive.ArchiveError, match="unknown presets"):
        archive.preset_items(root, "widget", {"absent"})


def test_normalization_uses_api_typed_selects_bounds_and_rejections(frozen):
    _, _, manifest = frozen
    assert archive.normalize_parameters(manifest, {"width": 500})["width"] == 200
    with pytest.raises(archive.ArchiveError, match="rejected"):
        archive.normalize_parameters(manifest, {"style": 99})
    with pytest.raises(archive.ArchiveError, match="rejected"):
        archive.normalize_parameters(manifest, {"invented": 2})
    with pytest.raises(archive.ArchiveError, match="non-finite"):
        archive.normalize_parameters(manifest, {"width": float("nan")})


def test_glb_roundtrip_scales_100mm_to_point1m_and_preserves_part_ids():
    import io
    np = pytest.importorskip("numpy")
    trimesh = pytest.importorskip("trimesh")
    mesh = trimesh.creation.box(extents=[100, 20, 10])
    mesh.apply_translation([50, 0, 5])  # non-centred origin makes recentering detectable
    data = archive.normalized_glb([("actual-body", mesh, (0.2, 0.3, 0.4))])
    scene = trimesh.load(io.BytesIO(data), file_type="glb", force="scene")
    assert "actual-body" in scene.graph.nodes_geometry
    assert np.allclose(scene.bounds, [[0, 0, -0.01], [0.1, 0.01, 0.01]])
    assert np.allclose(scene.extents, [0.1, 0.01, 0.02])
    transform = np.asarray(archive.FRAME["source_to_asset_matrix"])
    assert np.linalg.det(transform[:3, :3]) > 0  # right handed
    assert np.allclose(transform @ [0, 0, 100, 1], [0, 0.1, 0, 1])


def _built(frozen, runtime, producer, monkeypatch, tmp_path):
    root, pin, _ = frozen
    monkeypatch.setattr(archive, "runtime_identity", lambda: runtime)
    out = tmp_path / "archive"
    result = archive.build_archive(root, pin, ["widget"], out, {"small", "large"})
    assert not result["coverage"]["failed"]
    archive.check_archive(out, pin)
    return root, pin, out, result


def test_build_covers_each_preset_and_copies_only_committed_svg(frozen, runtime, producer, monkeypatch, tmp_path):
    root, pin, out, result = _built(frozen, runtime, producer, monkeypatch, tmp_path)
    assert len(result["entries"]) == 2
    assert producer == [("body", {"width": 50.0, "style": 1, "lid": 1}),
                        ("closure", {"width": 50.0, "style": 1, "lid": 1}),
                        ("body", {"width": 150.0, "style": 2, "lid": 1})]
    small, large = result["entries"]
    assert small["source"]["pin"] == pin
    assert small["source"]["params"] == {"width": 50, "style": "1"}
    svg = small["assets"]["svg"]
    assert (out / svg["path"]).read_bytes() == (root / svg["source_path"]).read_bytes()
    assert svg["verification"] == "committed-source-only"
    assert svg["frame"]["units"] == "svg-user-unit"
    assert "svg" not in large["assets"]  # no invented drawing for missing projections
    before = len(producer)
    archive.build_archive(root, pin, ["widget"], out, {"small", "large"})
    assert len(producer) == before  # verified cache hit


@pytest.mark.parametrize("change", ["missing", "stale", "parameters", "coverage", "parts", "runtime", "source", "asset_frame"])
def test_archive_check_rejects_missing_stale_and_incomplete(frozen, runtime, producer, monkeypatch, tmp_path, change):
    _, pin, out, manifest = _built(frozen, runtime, producer, monkeypatch, tmp_path)
    bad = copy.deepcopy(manifest)
    entry = bad["entries"][0]
    if change == "missing":
        (out / entry["assets"]["glb"]["path"]).unlink()
    elif change == "stale":
        (out / entry["assets"]["glb"]["path"]).write_bytes(b"replaced")
    elif change == "parameters":
        entry["resolved_parameters"]["width"] = 99
    elif change == "coverage":
        bad["entries"].pop()
    elif change == "parts":
        entry["parts"].append("invented")
    elif change == "runtime":
        entry["runtime"]["versions"]["test"] = "changed"
    elif change == "asset_frame":
        entry["assets"]["glb"]["frame"]["units"] = "mm"
    else:
        entry["source"]["files"][0]["sha256"] = "b" * 64
    (out / "manifest.json").write_text(json.dumps(bad))
    with pytest.raises(archive.ArchiveError):
        archive.check_archive(out, pin)


def test_check_refuses_another_full_pin(frozen, runtime, producer, monkeypatch, tmp_path):
    _, _, out, _ = _built(frozen, runtime, producer, monkeypatch, tmp_path)
    with pytest.raises(archive.ArchiveError, match="mismatch"):
        archive.check_archive(out, "b" * 40)


def test_changed_runtime_rerenders_and_missing_asset_is_not_a_cache_hit(frozen, runtime, producer, monkeypatch, tmp_path):
    root, pin, out, manifest = _built(frozen, runtime, producer, monkeypatch, tmp_path)
    (out / manifest["entries"][0]["assets"]["glb"]["path"]).unlink()
    before = len(producer)
    archive.build_archive(root, pin, ["widget"], out, {"small", "large"})
    assert len(producer) > before
    runtime["versions"]["test"] = "new-runtime"
    runtime["fingerprint"] = archive.digest({k: v for k, v in runtime.items() if k != "fingerprint"})
    before = len(producer)
    archive.build_archive(root, pin, ["widget"], out, {"small", "large"})
    assert len(producer) > before


def test_native_failure_is_recorded_and_never_published_as_success(frozen, runtime, producer, monkeypatch, tmp_path):
    root, pin, _ = frozen
    monkeypatch.setattr(archive, "runtime_identity", lambda: runtime)
    helpers = archive.native_helpers()
    helpers.run_cadquery_part = lambda *a, **k: (False, "sandbox rejection")
    monkeypatch.setattr(archive, "native_helpers", lambda: helpers)
    out = tmp_path / "failed-archive"
    result = archive.build_archive(root, pin, ["widget"], out, {"small"})
    assert result["entries"] == []
    assert "sandbox rejection" in result["coverage"]["failed"][0]["error"]
    with pytest.raises(archive.ArchiveError, match="coverage"):
        archive.check_archive(out, pin)


def test_zero_eligible_fold_states_is_not_success(frozen, runtime, monkeypatch, tmp_path):
    root, pin, _ = frozen
    monkeypatch.setattr(archive, "runtime_identity", lambda: runtime)
    with pytest.raises(archive.ArchiveError, match="zero coverage"):
        archive.build_archive(root, pin, ["widget"], tmp_path / "empty", {"folded"})


def test_paths_and_native_environment_do_not_escape_or_inherit_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("ARCHIVE_TEST_SECRET", "private-fixture")
    child = archive.native_environment(tmp_path)
    assert "ARCHIVE_TEST_SECRET" not in child
    assert child["PYTHONPATH"] == str(tmp_path)
    with pytest.raises(archive.ArchiveError, match="within"):
        archive.safe_file(tmp_path, "../escape.glb")
