"""Tests for the pure parts of ``scripts/dev/render_commons_models.py``.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_render_commons_models.py -q

The script drives a local API, which no test here starts. What is pinned is
what decides WHICH renders happen and WHEN they are redone:

  - keyframe interpolation mirrors the API's flipbook route (ints stay ints,
    non-numerics switch at the midpoint) but with linear ``t`` — a frame set
    that drifted from the API's would animate a different design;
  - the cartridge hash ignores docs and images and changes with the engine
    fingerprint, which is what makes the workflow's cache incremental rather
    than either stale or useless;
  - the production API is refused, whatever the flag says.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "dev" / "render_commons_models.py"


def _load():
    spec = importlib.util.spec_from_file_location("render_commons_models", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rcm = _load()


# ─── Keyframe interpolation ─────────────────────────────────────────────────


def test_numeric_params_interpolate_and_ints_stay_ints():
    out = rcm.interpolate_params({"teeth": 16, "pitch": 1.0}, {"teeth": 80, "pitch": 3.0}, 0.5)
    assert out == {"pitch": 2.0, "teeth": 48}
    assert isinstance(out["teeth"], int)


def test_non_numeric_params_switch_at_the_midpoint():
    frm = {"style": "round", "lid": False}
    to = {"style": "square", "lid": True}
    assert rcm.interpolate_params(frm, to, 0.49) == frm
    assert rcm.interpolate_params(frm, to, 0.5) == to
    # A bool is not a number here, even though Python says otherwise.
    assert rcm.interpolate_params({"lid": False}, {"lid": True}, 0.25) == {"lid": False}


def test_one_sided_keys_pass_through():
    assert rcm.interpolate_params({"a": 1}, {"b": 2}, 0.0) == {"a": 1, "b": 2}


def test_frame_items_are_linear_over_the_frames_and_named_by_index():
    manifest = {
        "modes": [{"id": "assembly"}, {"id": "exploded"}],
        "animations": [
            {"id": "ratio-sweep", "from_state": {"output_teeth": 16}, "to_state": {"output_teeth": 80}, "frames": 5},
            {"id": "blow-up", "from_state": {"gap": 0.0}, "to_state": {"gap": 10.0}, "frames": 3, "mode": "exploded"},
        ],
    }
    items = rcm.frame_items("gear-reducer", manifest)
    assert [i["file"] for i in items] == [
        "gear-reducer.ratio-sweep.0.glb",
        "gear-reducer.ratio-sweep.1.glb",
        "gear-reducer.ratio-sweep.2.glb",
        "gear-reducer.ratio-sweep.3.glb",
        "gear-reducer.ratio-sweep.4.glb",
        "gear-reducer.blow-up.0.glb",
        "gear-reducer.blow-up.1.glb",
        "gear-reducer.blow-up.2.glb",
    ]
    # Linear in t, not eased: equal steps of 16 teeth.
    assert [i["parameters"]["output_teeth"] for i in items[:5]] == [16, 32, 48, 64, 80]
    assert [i["mode"] for i in items[:5]] == ["assembly"] * 5
    assert [i["parameters"]["gap"] for i in items[5:]] == [0.0, 5.0, 10.0]
    assert [i["mode"] for i in items[5:]] == ["exploded"] * 3


def test_render_items_start_with_the_default_mode_at_manifest_defaults():
    manifest = {"modes": [{"id": "bin"}, {"id": "lid"}]}
    items = rcm.render_items("gridfinity", manifest)
    assert items == [{"file": "gridfinity.glb", "slug": "gridfinity", "mode": "bin", "parameters": {}, "label": "base"}]


# ─── Cartridge hashing ──────────────────────────────────────────────────────


def _cartridge(tmp_path: Path) -> Path:
    root = tmp_path / "widget"
    (root / "docs").mkdir(parents=True)
    (root / "project.json").write_text('{"modes": [{"id": "a"}]}')
    (root / "widget.py").write_text("print('geometry')\n")
    (root / "docs" / "README.md").write_text("# widget\n")
    (root / "thumb.png").write_bytes(b"\x89PNG")
    return root


def test_cartridge_hash_is_stable_and_ignores_docs_and_images(tmp_path):
    root = _cartridge(tmp_path)
    before = rcm.cartridge_hash(root, "engine=1")
    assert before == rcm.cartridge_hash(root, "engine=1")

    (root / "docs" / "README.md").write_text("# widget, revised\n")
    (root / "thumb.png").write_bytes(b"\x89PNG\x00")
    assert rcm.cartridge_hash(root, "engine=1") == before

    (root / "widget.py").write_text("print('new geometry')\n")
    assert rcm.cartridge_hash(root, "engine=1") != before


def test_cartridge_hash_changes_with_the_engine_fingerprint(tmp_path):
    root = _cartridge(tmp_path)
    assert rcm.cartridge_hash(root, "openscad=2021.01") != rcm.cartridge_hash(root, "openscad=2024.12")


def test_combined_digest_is_order_independent():
    a = rcm.combined_digest({"a": "1", "b": "2"})
    b = rcm.combined_digest({"b": "2", "a": "1"})
    assert a == b
    assert a != rcm.combined_digest({"a": "1", "b": "3"})


# ─── Worklist ───────────────────────────────────────────────────────────────


def test_worklist_drops_private_and_missing_cartridges(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text('{"cartridges": [{"slug": "public"}, {"slug": "secret"}, {"slug": "missing"}]}')
    projects = tmp_path / "projects"
    (projects / "public").mkdir(parents=True)
    (projects / "public" / "project.json").write_text('{"modes": [{"id": "a"}]}')
    (projects / "secret").mkdir()
    (projects / "secret" / "project.json").write_text('{"modes": [{"id": "a"}], "access_control": {"view": "private"}}')

    manifests, skipped = rcm.load_worklist(catalog, projects, None)
    assert list(manifests) == ["public"]
    assert any(s.startswith("secret: private") for s in skipped)
    assert any(s.startswith("missing: no manifest") for s in skipped)


def test_worklist_refuses_unknown_slugs(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text('{"cartridges": [{"slug": "public"}]}')
    with pytest.raises(rcm.SetupError, match="nope"):
        rcm.load_worklist(catalog, tmp_path / "projects", {"nope"})


# ─── Production guard ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "api",
    ["https://api.yantra4d.com", "https://API.yantra4d.com/", "https://staging.yantra4d.com", "https://yantra4d.com"],
)
def test_production_hosts_are_refused(api):
    with pytest.raises(rcm.SetupError, match="production"):
        rcm.check_api_base(api)


def test_local_api_is_accepted_and_normalised():
    assert rcm.check_api_base("http://localhost:5000/") == "http://localhost:5000"
    assert rcm.check_api_base("http://127.0.0.1:5000") == "http://127.0.0.1:5000"


def test_keyframes_snap_to_the_parameter_grid_like_the_slider():
    # motor-mount as shipped: nema_size min 17 / max 34 / step 6. Linear
    # interpolation gave 17, 21, 26, 30, 34 and the script mapped 21/26/30 to
    # its default — four identical frames (run 35460054814).
    manifest = {
        "modes": [{"id": "mount"}],
        "parameters": [
            {"id": "nema_size", "type": "slider", "min": 17, "max": 34, "step": 6},
            {"id": "wall_thickness", "type": "slider", "min": 3, "max": 8, "step": 0.5},
        ],
        "animations": [
            {"id": "nema-sweep", "from_state": {"nema_size": 17}, "to_state": {"nema_size": 34}, "frames": 5},
            {"id": "wall-sweep", "from_state": {"wall_thickness": 3}, "to_state": {"wall_thickness": 8}, "frames": 5},
        ],
    }
    items = rcm.frame_items("motor-mount", manifest)
    assert [i["parameters"]["nema_size"] for i in items[:5]] == [17, 23, 23, 29, 34]
    assert all(isinstance(i["parameters"]["nema_size"], int) for i in items[:5])
    # Integer interpolation lands on the 0.5 grid already; nothing changes, ints stay ints.
    assert [i["parameters"]["wall_thickness"] for i in items[5:]] == [3, 4, 6, 7, 8]
    assert all(isinstance(i["parameters"]["wall_thickness"], int) for i in items[5:])


def test_snap_to_parameter_grid_clamps_and_leaves_the_rest_alone():
    defs = [
        {"id": "teeth", "min": 8, "max": 40, "step": 4},
        {"id": "gap", "min": 0.0, "max": 1.0, "step": 0.25},
        {"id": "label", "type": "text"},
        {"id": "no_step", "min": 0, "max": 10},
    ]
    out = rcm.snap_to_parameter_grid(
        {"teeth": 41, "gap": 0.6, "label": "x", "no_step": 3.3, "lid": True, "undeclared": 2.2}, defs
    )
    assert out == {"teeth": 40, "gap": 0.5, "label": "x", "no_step": 3.3, "lid": True, "undeclared": 2.2}
    assert isinstance(out["teeth"], int)
    assert rcm.snap_to_parameter_grid({"teeth": 9}, defs) == {"teeth": 8}
    assert rcm.snap_to_parameter_grid({"teeth": -5}, defs) == {"teeth": 8}
    assert rcm.snap_to_parameter_grid({"teeth": 12}, None) == {"teeth": 12}
