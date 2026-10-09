"""GOC-1 generator output (services/engine/generator_output.py).

The golden vectors below were computed straight from the contract text
(GOC-1 §3) with nothing but ``hashlib`` and ``json`` — not with this module —
so a drift in the canonicalisation, the sort order or the line format of the
tree digest fails here before it reaches another producer or the checker.
"""
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import pytest

from config import Config
from services.engine import generator_output as go

# ── Golden vectors (GOC-1 §3) ─────────────────────────────────────────────
CONTRACT_EXAMPLE_PAIRS_BYTES = b'[["clearance",0.3],["mode_flag",true],["wall",null]]'
V1_CONTRACT_EXAMPLE = "c00f4dbbfbafc08f6a1866035db2d755919396e58aacaace0446f7160009fb45"
V2_EMPTY = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
V3_UNICODE_SORTED = "c6f05c7112bf7c7f729ead1c499209e09f3fbcb9eba69025a8acfe173e3003a9"
V4_INSTANCE = "2ebe181eef53e71288be2e1d36fe6ac2d201676b9345fc9d7d23d3f28a3f1a6c"
V5_INSTANCE_PART_NULL = "304f0166e2304c2fadd0ad90e02ceddaecaa76a867d50a6289ddaf7c798acbf2"
V6_TREE = "1d6677507231e5e642fc30eba6e962bb6a3de9fbe23f9a02d6cbb788cc934943"
V7_INTEGRAL = "990810333fa98ffdf815fd44526d054fbe249cb7c3db9c1ce63d372030705214"  # [["w",12]]


@pytest.fixture(autouse=True)
def _default_flags(monkeypatch):
    """Pin the three GOC-1 flags to their shipped defaults, whatever the environment says."""
    monkeypatch.setattr(Config, "RENDER_GENERATOR_OUTPUT", True)
    monkeypatch.setattr(Config, "RENDER_INJECT_FULL_PARAMS", False)
    monkeypatch.setattr(Config, "RENDER_MATERIAL_INJECTION", True)
    monkeypatch.setattr(Config, "COMMONS_SHA", "")
    go.commons_sha.cache_clear()
    yield
    go.commons_sha.cache_clear()


def _var(pid, value, source="request", vtype="number"):
    return {"id": pid, "value": value, "type": vtype, "source": source}


class TestGoldenVectors:
    def test_canonical_json_of_the_contract_example(self):
        pairs = [["clearance", 0.3], ["mode_flag", True], ["wall", None]]
        assert go.canonical_json(pairs) == CONTRACT_EXAMPLE_PAIRS_BYTES

    def test_variables_sha256_of_the_contract_example(self):
        variables = [_var("wall", None, "source_default"), _var("mode_flag", True, vtype="boolean"),
                     _var("clearance", 0.3)]
        assert go.variables_sha256(variables) == V1_CONTRACT_EXAMPLE

    def test_variables_sha256_ignores_provenance(self):
        a = [_var("clearance", 0.3, "request")]
        b = [{"id": "clearance", "value": 0.3, "type": "number", "source": "preset", "preset_id": "p",
              "unit": "mm", "measurement": "x"}]
        assert go.variables_sha256(a) == go.variables_sha256(b)

    def test_variables_sha256_of_an_empty_list(self):
        assert go.variables_sha256([]) == V2_EMPTY

    def test_ids_sort_bytewise_and_strings_stay_utf8(self):
        variables = [_var("beta_2", False, vtype="boolean"), _var("alpha", "ñandú", vtype="string"),
                     _var("Zeta", 1.5)]
        assert go.variables_sha256(variables) == V3_UNICODE_SORTED

    def test_instance_id(self):
        assert go.instance_id("tslot-corner", "corner_2way", "corner_2way", "0" * 64,
                              V1_CONTRACT_EXAMPLE) == V4_INSTANCE

    def test_instance_id_with_no_part(self):
        assert go.instance_id("tslot-corner", "corner_2way", None, "0" * 64, V1_CONTRACT_EXAMPLE) == V5_INSTANCE_PART_NULL

    def test_tree_sha256(self, tmp_path):
        _write(tmp_path, {"main.py": b"print(1)\n", "project.json": b"{}\n", "sub/a.scad": b"cube(1);\n"})
        assert go.compute_tree_sha256(tmp_path) == V6_TREE

    def test_integral_floats_hash_as_integers(self):
        """GOC-1 v1.0.1 §3.1: yantra4d holds sliders as floats; other producers hold ints."""
        assert go.canonical_json([["w", 12.0]]) == go.canonical_json([["w", 12]]) == b'[["w",12]]'
        assert go.variables_sha256([_var("w", 12.0)]) == go.variables_sha256([_var("w", 12)]) == V7_INTEGRAL
        assert go.canonical_json({"a": [-0.0, 1.5, True, 2.0 ** 53]}) == b'{"a":[0,1.5,true,9007199254740992.0]}'

    def test_canonical_json_refuses_nan(self):
        with pytest.raises(ValueError):
            go.canonical_json([["x", math.nan]])


def _write(root: Path, files: dict[str, bytes]) -> None:
    for rel, data in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


_BASE_TREE = {"main.py": b"print(1)\n", "project.json": b"{}\n", "sub/a.scad": b"cube(1);\n"}


class TestTreeDigest:
    BASE = MappingProxyType(_BASE_TREE)

    def test_excluded_paths_do_not_move_the_digest(self, tmp_path):
        _write(tmp_path, {
            **self.BASE,
            "README.md": b"x", "notes.TXT": b"x", "thumb.PNG": b"x", "img/a.jpeg": b"x", "a.svg": b"x",
            "b.webp": b"x", "c.gif": b"x", "d.pdf": b"x", "e.jpg": b"x",
            "docs/extra.scad": b"cube(2);", "__pycache__/m.pyc": b"x", "deep/node_modules/x.js": b"x",
            ".git": b"gitdir: elsewhere", "sub/.git/HEAD": b"ref",
        })
        assert go.compute_tree_sha256(tmp_path) == V6_TREE

    def test_docs_is_excluded_only_at_the_cartridge_root(self, tmp_path):
        _write(tmp_path, {**self.BASE, "sub/docs/part.scad": b"cube(3);"})
        assert go.compute_tree_sha256(tmp_path) != V6_TREE

    def test_file_symlinks_are_followed_directory_symlinks_are_not(self, tmp_path):
        cart = tmp_path / "cart"
        outside = tmp_path / "outside"
        _write(cart, self.BASE)
        _write(outside, {"lib.scad": b"sphere(1);"})
        os.symlink(outside, cart / "linked_dir")
        os.symlink(cart / "missing", cart / "dangling.scad")
        assert go.compute_tree_sha256(cart) == V6_TREE
        os.symlink(outside / "lib.scad", cart / "lib.scad")
        expected_lines = "".join(
            f"{hashlib.sha256(data).hexdigest()}  {rel}\n"
            for rel, data in sorted({**self.BASE, "lib.scad": b"sphere(1);"}.items(), key=lambda i: i[0].encode())
        )
        assert go.compute_tree_sha256(cart) == hashlib.sha256(expected_lines.encode()).hexdigest()

    def test_cached_digest_follows_an_edit(self, tmp_path):
        _write(tmp_path, self.BASE)
        first = go.tree_sha256(tmp_path)
        assert first == V6_TREE
        assert go.tree_sha256(tmp_path) == first
        (tmp_path / "main.py").write_bytes(b"print(2)\n")
        assert go.tree_sha256(tmp_path) != first


class TestHelpers:
    @pytest.mark.parametrize("name,expected", [
        ("x.stl", "model/stl"), ("x.STEP", "model/step"), ("x.glb", "model/gltf-binary"),
        ("x.3mf", "model/3mf"), ("x.off", "application/octet-stream"),
    ])
    def test_media_type(self, name, expected):
        assert go.media_type_for(name) == expected

    def test_sidecar_names(self):
        assert go.sidecar_name("a_preview_1_b.stl") == "a_preview_1_b.stl.variables.json"
        assert go.is_sidecar_name("A.STL.VARIABLES.JSON")
        assert go.described_artifact_name("a_preview_1_b.stl.variables.json") == "a_preview_1_b.stl"
        assert go.described_artifact_name("a.stl") == "a.stl"

    @pytest.mark.parametrize("key,physical", [
        ("target_material", True), ("mat_shrinkage_x", True), ("thermo_melting_temp", True),
        ("infill", True), ("mat_thick", False), ("clearance", False), ("printer_profile", True),
    ])
    def test_physical_denylist(self, key, physical):
        assert go.is_physical_key(key) is physical

    def test_output_summary_and_envelope_fields(self):
        inputs = {"variables": [], "variables_sha256": V2_EMPTY, "complete": True}
        assert go.output_summary(None) is None
        assert go.envelope_fields({}) == {}
        assert go.envelope_fields({"generator_inputs": inputs}) == {
            "generator_output": {"format_version": "1.0.0", "complete": True, "variables_sha256": V2_EMPTY}}

    def test_engine_kernel(self, monkeypatch):
        monkeypatch.setattr("services.engine.openscad.backend_cache_signature", lambda: "Manifold|v1")
        assert go.engine_kernel("openscad") == "openscad Manifold|v1"
        assert go.engine_kernel("cadquery").startswith("cadquery ")
        assert go.engine_kernel("graph").startswith("cadquery ")
        assert go.engine_kernel("implicit").startswith("yantra4d-implicit numpy ")
        assert go.engine_kernel("unknown") is None

    def test_engine_kernel_survives_a_failing_probe(self, monkeypatch):
        def boom():
            raise RuntimeError("no openscad")
        monkeypatch.setattr("services.engine.openscad.backend_cache_signature", boom)
        assert go.engine_kernel("openscad") is None


# ── Parameter resolution ──────────────────────────────────────────────────

MANIFEST = {
    "project": {"name": "Demo", "slug": "demo", "version": "2.1.0"},
    "modes": [
        {"id": "unit", "scad_file": "main.scad", "label": "Unit", "parts": ["body"],
         "estimate": {"base_units": 1, "formula": "constant"}},
        {"id": "other", "scad_file": "main.scad", "label": "Other", "parts": ["body"],
         "estimate": {"base_units": 1, "formula": "constant"}},
    ],
    "parts": [{"id": "body", "render_mode": 0, "label": "Body", "default_color": "#fff"}],
    "parameters": [
        {"id": "width", "type": "slider", "default": 40, "min": 10, "max": 100, "modes": ["unit", "other"]},
        {"id": "depth", "type": "slider", "default": 20, "min": 5, "max": 50, "modes": ["unit"]},
        {"id": "lid", "type": "checkbox", "default": True},
        {"id": "teeth", "type": "select", "default": 12, "options": [{"value": 12}, {"value": 24}]},
        {"id": "style", "type": "select", "default": "round", "options": [{"value": "round"}, {"value": "flat"}]},
        {"id": "label", "type": "text", "default": "Demo", "maxlength": 8},
        {"id": "only_other", "type": "slider", "default": 3, "min": 0, "max": 9, "visible_in_modes": ["other"]},
        {"id": "neck_girth", "type": "slider", "default": 380, "min": 300, "max": 450,
         "measurement": {"standard": "iso_8559", "code": "neck_girth"}},
        {"id": "target_material", "type": "select", "default": "pla",
         "options": [{"value": "pla"}, {"value": "petg"}]},
        {"id": "target_part", "type": "select", "default": "body", "options": [{"value": "body"}]},
    ],
    "estimate_constants": {"base_time": 1, "per_unit": 0.1, "per_part": 0.5},
}


@pytest.fixture
def demo(tmp_path):
    """A real cartridge on disk under PROJECTS_DIR (conftest points it at tmp_path)."""
    cart = tmp_path / "demo"
    cart.mkdir()
    (cart / "project.json").write_text(json.dumps(MANIFEST))
    (cart / "main.scad").write_text("cube(width);\n")
    go.commons_sha.cache_clear()
    from manifest import get_manifest
    return get_manifest("demo")


def _by_id(variables):
    return {v["id"]: v for v in variables}


class TestResolveEffectiveParameters:
    def test_unsent_parameters_are_source_default_null(self, demo):
        resolved = go.resolve_effective_parameters(demo, "unit", {"width": 55}, inject_full=False)
        assert resolved.engine_params == {"width": 55.0}
        variables = _by_id(resolved.variables)
        assert variables["width"] == {"id": "width", "value": 55.0, "type": "number", "source": "request"}
        assert variables["depth"] == {"id": "depth", "value": None, "type": "number", "source": "source_default"}
        assert variables["lid"]["type"] == "boolean" and variables["lid"]["value"] is None
        assert variables["teeth"]["type"] == "number"
        assert variables["style"]["type"] == "string"
        assert variables["label"]["type"] == "string"
        assert [v["id"] for v in resolved.variables] == sorted(variables, key=str.encode)

    def test_values_keep_their_manifest_types_after_validation(self, demo):
        raw = {"width": "500", "lid": True, "teeth": "24", "style": "flat", "label": "abcdefghijk"}
        resolved = go.resolve_effective_parameters(demo, "unit", raw, inject_full=False)
        assert resolved.engine_params["width"] == 100.0  # clamped
        assert resolved.engine_params["lid"] == 1  # what OpenSCAD receives
        variables = _by_id(resolved.variables)
        assert variables["width"]["value"] == 100.0
        assert variables["lid"] == {"id": "lid", "value": True, "type": "boolean", "source": "request"}
        assert variables["teeth"]["value"] == 24 and variables["teeth"]["type"] == "number"
        assert variables["label"]["value"] == "abcdefgh"

    def test_no_mode_scoping_and_no_engine_control_keys(self, demo):
        """GOC-1 v1.0.1 §4.1: every declared parameter, whatever its modes/visible_in_modes."""
        resolved = go.resolve_effective_parameters(demo, "unit", {"target_part": "body"}, inject_full=False)
        ids = {v["id"] for v in resolved.variables}
        assert "only_other" in ids  # visible_in_modes ["other"] is a UI hint, not engine relevance
        assert "target_part" not in ids  # engine control, never a variable
        other = go.resolve_effective_parameters(demo, "other", {"depth": 7}, inject_full=False)
        assert {v["id"] for v in other.variables} == ids
        assert _by_id(other.variables)["depth"]["value"] == 7.0

    def test_unknown_invalid_and_non_finite_values_are_not_injected(self, demo):
        raw = {"bogus": 1, "style": "zigzag", "width": "nan", "depth": "inf"}
        resolved = go.resolve_effective_parameters(demo, "unit", raw, inject_full=False)
        assert "bogus" not in resolved.engine_params
        assert "style" not in resolved.engine_params
        assert "width" not in resolved.engine_params
        assert resolved.engine_params["depth"] == 50.0  # inf clamps to max
        assert _by_id(resolved.variables)["width"]["source"] == "source_default"

    def test_physical_parameters_never_become_variables(self, demo):
        resolved = go.resolve_effective_parameters(demo, "unit", {"target_material": "petg"}, inject_full=False)
        assert "target_material" not in {v["id"] for v in resolved.variables}
        assert resolved.legacy_physical_inputs == {"target_material": "petg"}

    def test_measurement_code_is_recorded(self, demo):
        resolved = go.resolve_effective_parameters(demo, "unit", {}, inject_full=False)
        assert _by_id(resolved.variables)["neck_girth"]["measurement"] == "neck_girth"

    def test_inject_full_injects_every_default_but_no_physical_or_control_ones(self, demo):
        resolved = go.resolve_effective_parameters(demo, "unit", {"width": 60}, inject_full=True)
        variables = _by_id(resolved.variables)
        assert variables["width"]["source"] == "request"
        assert variables["depth"] == {"id": "depth", "value": 20.0, "type": "number", "source": "manifest_default"}
        assert variables["lid"]["value"] is True
        assert resolved.engine_params["lid"] == 1
        assert resolved.engine_params["only_other"] == 3.0
        assert "target_material" not in resolved.engine_params
        assert "target_part" not in resolved.engine_params
        assert all(v["source"] != "source_default" for v in resolved.variables)

    def test_a_custom_validator_is_honoured(self, demo):
        resolved = go.resolve_effective_parameters(demo, "unit", {"width": 3}, inject_full=False,
                                                   validate=lambda raw: dict(raw))
        assert resolved.engine_params == {"width": 3}

    def test_a_non_dict_payload_resolves_to_nothing_sent(self, demo):
        resolved = go.resolve_effective_parameters(demo, "unit", None, inject_full=False)
        assert resolved.engine_params == {}


class TestResolveRenderInputs:
    @staticmethod
    def _injector(params, material):
        params["mat_shrinkage_x"] = 1.002
        params["thermo_glass_transition_temp"] = 61.0

    def test_default_flags_keep_todays_material_injection_out_of_variables(self, demo, monkeypatch):
        params, inputs = go.resolve_render_inputs(
            demo, "unit", {"width": 50, "target_material": "petg"}, material_injector=self._injector)
        assert params["mat_shrinkage_x"] == 1.002 and params["target_material"] == "petg"
        assert inputs["legacy_physical_inputs"] == {
            "target_material": "petg", "mat_shrinkage_x": 1.002, "thermo_glass_transition_temp": 61.0}
        assert not any(go.is_physical_key(v["id"]) for v in inputs["variables"])
        assert inputs["complete"] is False
        assert inputs["variables_sha256"] == go.variables_sha256(inputs["variables"])

    def test_material_injection_off_strips_target_material(self, demo, monkeypatch):
        monkeypatch.setattr(Config, "RENDER_MATERIAL_INJECTION", False)
        calls = []
        params, inputs = go.resolve_render_inputs(
            demo, "unit", {"target_material": "petg"}, material_injector=lambda *a: calls.append(a))
        assert calls == []
        assert "target_material" not in params
        assert "legacy_physical_inputs" not in inputs

    def test_inject_full_makes_the_instance_complete(self, demo, monkeypatch):
        monkeypatch.setattr(Config, "RENDER_INJECT_FULL_PARAMS", True)
        _params, inputs = go.resolve_render_inputs(demo, "unit", {}, material_injector=self._injector)
        assert inputs["complete"] is True

    def test_generator_output_off_changes_nothing_but_the_inputs(self, demo, monkeypatch):
        monkeypatch.setattr(Config, "RENDER_GENERATOR_OUTPUT", False)
        params, inputs = go.resolve_render_inputs(demo, "unit", {"width": 50}, material_injector=self._injector)
        assert params == {"width": 50.0}
        assert inputs is None

    def test_an_unusual_material_value_is_recorded_as_a_string(self, demo):
        _params, inputs = go.resolve_render_inputs(
            demo, "unit", {"target_material": ["x"]}, material_injector=lambda *a: None)
        assert inputs["legacy_physical_inputs"]["target_material"] == "['x']"


# ── Document and worker seam ──────────────────────────────────────────────

def _inputs(demo):
    _params, inputs = go.resolve_render_inputs(demo, "unit", {"width": 50, "target_material": "pla"},
                                               material_injector=lambda p, m: p.update(mat_clear_press=0.1))
    return inputs


class TestBuildGeneratorOutput:
    def test_document_shape_and_digests(self, demo, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "COMMONS_SHA", "ABCDEF1")
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        go.commons_sha.cache_clear()
        inputs = _inputs(demo)
        geometry = [{"path": "x.stl", "media_type": "model/stl", "sha256": "1" * 64, "bytes": 3,
                     "units": "mm", "role": "primary"}]
        doc = go.build_generator_output(demo, inputs, mode="unit", part="body", engine="openscad",
                                        entry_path=str(tmp_path / "demo" / "main.scad"), geometry=geometry,
                                        platform_build="build-1", kernel="openscad test")
        tree = go.compute_tree_sha256(tmp_path / "demo")
        assert doc["format"] == "hyperobjects.generator-output" and doc["format_version"] == "1.0.0"
        assert doc["kind"] == "solid"
        gen = doc["generator"]
        assert gen == {
            "platform": "yantra4d", "cartridge": "demo", "mode": "unit", "part": "body", "engine": "openscad",
            "platform_build": "build-1", "cartridge_version": "2.1.0", "kernel": "openscad test",
            "commons": {"repo": "solid-hyperobjects", "sha": "abcdef1"},
            "source": {"tree_sha256": tree, "tree_algorithm": "hyperobjects-tree-v1", "entry": "main.scad",
                       "entry_sha256": hashlib.sha256(b"cube(width);\n").hexdigest()},
        }
        assert doc["variables_sha256"] == go.variables_sha256(doc["variables"])
        assert doc["instance_id"] == go.instance_id("demo", "unit", "body", tree, doc["variables_sha256"])
        assert doc["legacy_physical_inputs"] == {"target_material": "pla", "mat_clear_press": 0.1}
        assert doc["complete"] is False
        assert "created_at" not in doc

    def test_the_instance_id_is_deploy_independent(self, demo, tmp_path):
        inputs = _inputs(demo)
        kw = {"mode": "unit", "part": "body", "engine": "openscad", "entry_path": None, "geometry": []}
        a = go.build_generator_output(demo, inputs, platform_build="one", kernel="k1", **kw)
        b = go.build_generator_output(demo, inputs, platform_build="two", kernel="k2", **kw)
        assert a["instance_id"] == b["instance_id"]

    def test_a_cartridge_outside_the_commons_records_no_commons(self, demo, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path / "elsewhere")
        doc = go.build_generator_output(demo, _inputs(demo), mode="unit", part=None, engine="openscad",
                                        entry_path=None, geometry=[])
        assert "commons" not in doc["generator"]
        assert "entry" not in doc["generator"]["source"]

    def test_an_entry_outside_the_cartridge_is_named_by_its_file(self, demo, tmp_path):
        script = tmp_path / "graphgen.py"
        script.write_text("x = 1\n")
        doc = go.build_generator_output(demo, _inputs(demo), mode="unit", part="body", engine="graph",
                                        entry_path=str(script), geometry=[])
        assert doc["generator"]["source"]["entry"] == "graphgen.py"

    def test_an_invalid_cartridge_slug_is_refused(self, demo):
        bad = SimpleNamespace(slug="Bad Slug", project={}, project_dir=demo.project_dir, parameters=[])
        with pytest.raises(ValueError):
            go.build_generator_output(bad, _inputs(demo), mode="unit", part="body", engine="openscad",
                                      entry_path=None, geometry=[])


class TestCommonsSha:
    def test_a_configured_sha_wins_and_a_malformed_one_is_dropped(self, monkeypatch):
        monkeypatch.setattr(Config, "COMMONS_SHA", "faaea08")
        go.commons_sha.cache_clear()
        assert go.commons_sha() == "faaea08"
        monkeypatch.setattr(Config, "COMMONS_SHA", "not-a-sha")
        go.commons_sha.cache_clear()
        assert go.commons_sha() is None
        go.commons_sha.cache_clear()

    def test_a_git_checkout_answers_for_itself(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "COMMONS_SHA", "")
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        (tmp_path / "f").write_text("x")
        git = ["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "add", "f"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "x"], check=True)
        head = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        go.commons_sha.cache_clear()
        assert go.commons_sha() == head
        go.commons_sha.cache_clear()

    def test_no_git_and_no_config_records_only_the_repo(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "COMMONS_SHA", "")
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        go.commons_sha.cache_clear()
        assert go.commons_sha() is None
        go.commons_sha.cache_clear()


class TestPreparePartOutput:
    def _task(self, demo, inputs, tmp_path):
        return {"engine": "openscad", "part": "body", "scad_path": str(tmp_path / "demo" / "main.scad"),
                "payload": {"project_slug": "demo", "mode": "unit", "render_revision": "rev-1",
                            "generator_inputs": inputs}}

    def test_writes_a_canonical_sidecar_next_to_the_served_file(self, demo, tmp_path, monkeypatch):
        monkeypatch.setattr("services.engine.openscad.backend_cache_signature", lambda: "Manifold|v1")
        out = tmp_path / "static"
        out.mkdir()
        serve, viewer = out / "demo_preview_1_body.stl", out / "demo_preview_1_body.glb"
        serve.write_bytes(b"solid\n")
        viewer.write_bytes(b"glTF")
        part = go.prepare_part_output(self._task(demo, _inputs(demo), tmp_path), demo, str(serve), str(viewer))
        assert part.sidecar_path == str(out / "demo_preview_1_body.stl.variables.json")
        raw = Path(part.sidecar_path).read_bytes()
        doc = json.loads(raw)
        assert raw == go.canonical_json(doc)
        assert [g["role"] for g in doc["geometry"]] == ["primary", "viewer"]
        assert doc["geometry"][0] == {"path": serve.name, "media_type": "model/stl",
                                      "sha256": hashlib.sha256(b"solid\n").hexdigest(), "bytes": 6,
                                      "units": "mm", "role": "primary"}
        assert doc["generator"]["platform_build"] == "rev-1"
        assert part.sha256 == doc["geometry"][0]["sha256"]
        assert part.instance_id == doc["instance_id"]
        published = {part.sidecar_path: "demo_preview_1_body.stl.variables.json"}
        assert part.part_fields(published) == {
            "sha256": part.sha256, "media_type": "model/stl", "instance_id": part.instance_id,
            "variables_url": "/static/demo_preview_1_body.stl.variables.json"}
        assert part.cache_fields(published)["variables_key"] == "demo_preview_1_body.stl.variables.json"

    def test_nothing_without_generator_inputs_or_with_the_flag_off(self, demo, tmp_path, monkeypatch):
        serve = tmp_path / "x.stl"
        serve.write_bytes(b"x")
        assert go.prepare_part_output(self._task(demo, None, tmp_path), demo, str(serve), None) is None
        monkeypatch.setattr(Config, "RENDER_GENERATOR_OUTPUT", False)
        assert go.prepare_part_output(self._task(demo, _inputs(demo), tmp_path), demo, str(serve), None) is None

    def test_a_failure_is_logged_and_the_part_is_served_without_it(self, demo, tmp_path, caplog):
        task = self._task(demo, _inputs(demo), tmp_path)
        with caplog.at_level("ERROR"):
            assert go.prepare_part_output(task, demo, str(tmp_path / "missing.stl"), None) is None
        assert any("could not be written" in r.getMessage() for r in caplog.records)


class TestCacheSeam:
    ENTRY = MappingProxyType({"key": "a.stl", "size_bytes": 1, "ts": 0, "sha256": "a" * 64, "media_type": "model/stl",
             "instance_id": "b" * 64, "variables_key": "a.stl.variables.json"})

    def test_part_fields_from_cache(self):
        assert go.part_fields_from_cache(dict(self.ENTRY)) == {
            "sha256": "a" * 64, "media_type": "model/stl", "instance_id": "b" * 64,
            "variables_url": "/static/a.stl.variables.json"}
        assert go.part_fields_from_cache({"key": "a.stl"}) == {}
        assert go.part_fields_from_cache(None) == {}

    def test_cache_entry_usable(self, monkeypatch):
        payload = {"generator_inputs": {"variables": []}}
        assert go.cache_entry_usable(dict(self.ENTRY), payload) is True
        assert go.cache_entry_usable({"key": "a.stl"}, payload) is False
        assert go.cache_entry_usable({**self.ENTRY, "sha256": "nope"}, payload) is False
        assert go.cache_entry_usable(None, payload) is False
        assert go.cache_entry_usable({"key": "a.stl"}, {}) is True
        monkeypatch.setattr(Config, "RENDER_GENERATOR_OUTPUT", False)
        assert go.cache_entry_usable({"key": "a.stl"}, payload) is True
