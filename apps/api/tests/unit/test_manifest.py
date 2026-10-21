"""Tests for manifest.py — ProjectManifest, load/get/discover/invalidate_cache."""
import json

import pytest

from manifest import (
    ProjectManifest,
    discover_projects,
    get_manifest,
    invalidate_cache,
    load_manifest,
)


def _write_manifest(tmp_path, slug="demo", extra=None):
    """Helper: write a minimal valid project.json and return its dir."""
    project_dir = tmp_path / slug
    project_dir.mkdir(exist_ok=True)
    data = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Demo", "slug": slug, "version": "1.0.0", "description": "A demo project"},
        "modes": [{"id": "single", "scad_file": "main.scad", "label": "Single", "parts": ["body"], "estimate": {"base_units": 1}}],
        "parts": [{"id": "body", "render_mode": 0, "label": "Body", "default_color": "#cccccc"}],
        "parameters": [{"id": "width", "type": "slider", "default": 10, "min": 1, "max": 100, "label": "Width"}],
        "estimate_constants": {"base_time": 2, "per_unit": 1, "per_part": 0.5},
    }
    if extra:
        data.update(extra)
    (project_dir / "project.json").write_text(json.dumps(data))
    (project_dir / "main.scad").write_text("cube([10,10,10]);")
    return project_dir


# ---- ProjectManifest accessors ----

class TestProjectManifest:
    def test_slug(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.slug == "demo"

    def test_modes(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert len(m.modes) == 1
        assert m.modes[0]["id"] == "single"

    def test_get_allowed_files(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        allowed = m.get_allowed_files()
        assert "main.scad" in allowed
        assert allowed["main.scad"] == d / "main.scad"

    def test_get_parts_for_mode(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.get_parts_for_mode("single") == ["body"]
        assert m.get_parts_for_mode("nonexistent") == []

    def test_get_scad_file_for_mode(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.get_scad_file_for_mode("single") == "main.scad"
        assert m.get_scad_file_for_mode("nonexistent") is None

    def test_calculate_estimate_units(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.calculate_estimate_units("single", {}) == 1

    def test_as_json(self, tmp_path):
        d = _write_manifest(tmp_path)
        raw = json.loads((d / "project.json").read_text())
        m = ProjectManifest(raw, d)
        assert m.as_json() == raw

    def test_engine_default_openscad(self, tmp_path):
        d = _write_manifest(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.engine == "openscad"

    def test_engine_cadquery(self, tmp_path):
        d = _write_manifest(tmp_path, extra={"project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "CQ", "slug": "cq", "version": "1.0.0", "description": "CQ test", "engine": "cadquery"}})
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.engine == "cadquery"

    def test_engine_implicit_from_field(self, tmp_path):
        d = _write_manifest(tmp_path, extra={"project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Imp", "slug": "imp", "version": "1.0.0", "description": "Implicit test", "hyperobject": {"is_hyperobject": True, "implicit_field": {"type": "tpms"}}}})
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.engine == "implicit"

    def test_engine_unknown_falls_back(self, tmp_path):
        d = _write_manifest(tmp_path, extra={"project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Bad", "slug": "bad", "version": "1.0.0", "description": "Bad engine", "engine": "blender"}})
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.engine == "openscad"


class TestModeEngine:
    """Per-mode engine resolution — the dual-engine cartridge feature.

    Precedence: explicit mode `engine` > inference from scad_file extension
    (.py/.cq -> cadquery) > project-level engine. An `implicit` project always
    renders every mode with the implicit engine.
    """

    def _dual(self, tmp_path):
        # project.engine defaults to openscad; modes mix .scad and .py + explicit overrides
        return _write_manifest(tmp_path, extra={
            "modes": [
                {"id": "scad_mode", "scad_file": "part.scad", "label": "S", "parts": ["a"], "estimate": {"base_units": 1}},
                {"id": "cq_mode", "scad_file": "main.py", "label": "C", "parts": ["b"], "estimate": {"base_units": 1}},
                {"id": "forced_cq", "scad_file": "x.scad", "engine": "cadquery", "label": "F", "parts": ["c"], "estimate": {"base_units": 1}},
                {"id": "forced_scad", "scad_file": "main.py", "engine": "openscad", "label": "G", "parts": ["d"], "estimate": {"base_units": 1}},
            ],
        })

    def test_mode_engine_fallback_to_project(self, tmp_path):
        d = self._dual(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.mode_engine("scad_mode") == "openscad"  # .scad + project default

    def test_mode_engine_inferred_from_py(self, tmp_path):
        d = self._dual(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.mode_engine("cq_mode") == "cadquery"  # .py scad_file infers cadquery

    def test_mode_engine_explicit_override_wins(self, tmp_path):
        d = self._dual(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.mode_engine("forced_cq") == "cadquery"    # explicit beats .scad
        assert m.mode_engine("forced_scad") == "openscad"  # explicit beats .py inference

    def test_mode_engine_none_returns_project_default(self, tmp_path):
        d = self._dual(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.mode_engine(None) == "openscad"

    def test_mode_engine_unknown_mode_returns_project_default(self, tmp_path):
        d = self._dual(tmp_path)
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        assert m.mode_engine("does_not_exist") == "openscad"

    def test_mode_engine_implicit_project_overrides_all(self, tmp_path):
        d = _write_manifest(tmp_path, extra={
            "project": {"thumbnail": "t.png", "tags": ["x"], "difficulty": "beginner", "name": "I", "slug": "i", "version": "1.0.0", "description": "d", "hyperobject": {"is_hyperobject": True, "implicit_field": {"type": "tpms"}}},
            "modes": [{"id": "cq_mode", "scad_file": "main.py", "engine": "cadquery", "label": "C", "parts": ["b"], "estimate": {"base_units": 1}}],
        })
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        # implicit projects render every mode with implicit, ignoring per-mode hints
        assert m.mode_engine("cq_mode") == "implicit"

    def test_bom_hardware_structure(self, tmp_path):
        bom = {
            "hardware": [
                {
                    "id": "magnets_6x2",
                    "label": {"en": "Magnets"},
                    "quantity_formula": "(enable_magnets ? 4 : 0)",
                    "unit": "pcs",
                },
                {
                    "id": "screws_m3x6",
                    "label": {"en": "Screws"},
                    "quantity_formula": "(enable_screws ? 4 : 0)",
                    "unit": "pcs",
                },
            ]
        }
        d = _write_manifest(tmp_path, extra={"bom": bom})
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        raw = m.as_json()
        assert "bom" in raw
        assert "hardware" in raw["bom"]
        assert len(raw["bom"]["hardware"]) == 2
        assert raw["bom"]["hardware"][0]["id"] == "magnets_6x2"
        assert raw["bom"]["hardware"][0]["quantity_formula"] == "(enable_magnets ? 4 : 0)"
        assert raw["bom"]["hardware"][0]["unit"] == "pcs"

    def test_constraints_structure(self, tmp_path):
        constraints = [
            {
                "rule": "width * depth <= 24",
                "message": {"en": "Max 24 cells"},
                "severity": "warning",
                "applies_to": ["width", "depth"],
            }
        ]
        d = _write_manifest(tmp_path, extra={"constraints": constraints})
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        raw = m.as_json()
        assert "constraints" in raw
        assert len(raw["constraints"]) == 1
        assert raw["constraints"][0]["rule"] == "width * depth <= 24"
        assert raw["constraints"][0]["severity"] == "warning"
        assert raw["constraints"][0]["applies_to"] == ["width", "depth"]

    def test_parameter_groups_structure(self, tmp_path):
        groups = [
            {"id": "dims", "label": {"en": "Dimensions"}},
            {
                "id": "features",
                "label": {"en": "Features"},
                "levels": [
                    {"id": "basic", "label": {"en": "Basic"}},
                    {"id": "advanced", "label": {"en": "Advanced"}},
                ],
            },
        ]
        d = _write_manifest(tmp_path, extra={"parameter_groups": groups})
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        raw = m.as_json()
        assert len(raw["parameter_groups"]) == 2
        assert raw["parameter_groups"][1]["levels"][0]["id"] == "basic"

    def test_grid_presets_structure(self, tmp_path):
        presets = {
            "rendering": {
                "emoji": "🪽",
                "label": {"en": "Quick Preview"},
                "values": {"width": 2},
            },
            "manufacturing": {
                "emoji": "⭐",
                "label": {"en": "Large"},
                "values": {"width": 4},
            },
            "default": "rendering",
        }
        d = _write_manifest(tmp_path, extra={"grid_presets": presets})
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        raw = m.as_json()
        assert raw["grid_presets"]["default"] == "rendering"
        assert raw["grid_presets"]["rendering"]["values"]["width"] == 2

    def test_viewer_config_structure(self, tmp_path):
        d = _write_manifest(tmp_path, extra={"viewer": {"default_color": "#4a90d9"}})
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        raw = m.as_json()
        assert raw["viewer"]["default_color"] == "#4a90d9"


# ---- discover_projects ----

class TestDiscoverProjects:
    def test_discovers_project(self, tmp_path):
        _write_manifest(tmp_path, "alpha")
        _write_manifest(tmp_path, "beta")
        projects = discover_projects()
        slugs = [p["slug"] for p in projects]
        assert "alpha" in slugs
        assert "beta" in slugs

    def test_no_path_key(self, tmp_path):
        _write_manifest(tmp_path, "alpha")
        projects = discover_projects()
        for p in projects:
            assert "path" not in p

    def test_empty_projects_dir(self, tmp_path):
        # tmp_path exists but has no subdirs with project.json
        projects = discover_projects()
        assert projects == []

    def test_invalid_json_skipped(self, tmp_path):
        bad_dir = tmp_path / "bad"
        bad_dir.mkdir()
        (bad_dir / "project.json").write_text("{invalid json")
        projects = discover_projects()
        assert len(projects) == 0


# ---- load_manifest / get_manifest ----

class TestLoadManifest:
    def test_loads_and_caches(self, tmp_path):
        _write_manifest(tmp_path, "test")
        m1 = load_manifest("test")
        m2 = get_manifest("test")
        assert m1 is m2

    def test_missing_manifest_raises(self, tmp_path):
        with pytest.raises(RuntimeError, match="not found"):
            load_manifest("nonexistent")

    def test_invalid_json_raises(self, tmp_path):
        bad_dir = tmp_path / "badjson"
        bad_dir.mkdir()
        (bad_dir / "project.json").write_text("{bad")
        with pytest.raises(RuntimeError, match="invalid JSON"):
            load_manifest("badjson")


# ---- invalidate_cache ----

class TestInvalidateCache:
    def test_invalidate_forces_reload(self, tmp_path):
        _write_manifest(tmp_path, "cached")
        m1 = load_manifest("cached")
        invalidate_cache("cached")
        m2 = load_manifest("cached")
        assert m1 is not m2


class TestResolveWithinProject:
    """A manifest-declared file name must stay inside the cartridge directory."""

    def _manifest(self, tmp_path):
        d = _write_manifest(tmp_path)
        return ProjectManifest(json.loads((d / "project.json").read_text()), d)

    def test_plain_name_resolves(self, tmp_path):
        m = self._manifest(tmp_path)
        resolved = m.resolve_within_project("main.scad")
        assert resolved == (m.project_dir / "main.scad").resolve()

    @pytest.mark.parametrize("bad", [
        "../escape.scad", "../../etc/passwd", "sub/../../escape.py", "/abs/path.scad",
    ])
    def test_escaping_name_is_refused(self, tmp_path, bad):
        m = self._manifest(tmp_path)
        with pytest.raises(ValueError, match="cartridge directory"):
            m.resolve_within_project(bad)

    def test_symlink_escaping_is_refused(self, tmp_path):
        m = self._manifest(tmp_path)
        outside = tmp_path.parent / "outside.scad"
        outside.write_text("cube(1);")
        link = m.project_dir / "link.scad"
        link.symlink_to(outside)
        with pytest.raises(ValueError, match="outside the cartridge directory"):
            m.resolve_within_project("link.scad")

    def test_get_allowed_files_drops_escaping_mode(self, tmp_path):
        d = _write_manifest(tmp_path, extra={
            "modes": [
                {"id": "ok", "scad_file": "main.scad", "parts": ["body"]},
                {"id": "evil", "scad_file": "../../evil.scad", "parts": ["body"]},
            ],
        })
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        allowed = m.get_allowed_files()
        assert "main.scad" in allowed
        assert "../../evil.scad" not in allowed


class TestResolveWithinDir:
    """The type-agnostic containment helper used by the render orchestrator."""

    def test_plain_name_from_start_dir(self, tmp_path):
        from manifest import resolve_within_dir
        (tmp_path / "sub").mkdir()
        got = resolve_within_dir(tmp_path, "part.py", start=tmp_path / "sub")
        assert got == (tmp_path / "sub" / "part.py").resolve()

    @pytest.mark.parametrize("bad", ["../x.py", "/etc/hosts", "a/../../x.py"])
    def test_escape_refused(self, tmp_path, bad):
        from manifest import resolve_within_dir
        with pytest.raises(ValueError, match="cartridge directory"):
            resolve_within_dir(tmp_path, bad)


class TestManifestFileNamesArePlainRelativePaths:
    """Manifest file references: a base rule for every cartridge, plus a strict
    character class for user-authored cartridges."""

    # Refused for every cartridge, curated or user-authored.
    ALWAYS_REFUSED = (
        "main.py\nimport os",          # newline (would break out of a comment)
        "main\r.py",                   # carriage return
        "main\x00.py",                 # NUL
        "main\x1b.py",                 # other control character
        "main\t.py",                   # tab is a control character
        "main\x7f.py",                 # DEL
        "../escape.py",                # parent segment
        "sub/../main.py",              # parent segment mid-path
        "/abs/main.py",                # absolute
        "",                            # empty
        "a" * 256,                     # over length
        None, 42, ("main.py",),        # not a string
    )
    # Refused only for user-authored cartridges.
    STRICT_ONLY_REFUSED = (
        "main file.py",                # space
        "mäin.py",                     # non-ASCII
        "main\\file.py",               # backslash
        "./main.py",                   # current-dir segment
        "sub//main.py",                # empty segment
        "main+v2.scad",                # outside the class
    )
    ACCEPTED = ("main.py", "main.scad", "sub/part.py", "model.graph.json", "parts/a-b_c.stl")

    @pytest.mark.parametrize("strict", [True, False])
    @pytest.mark.parametrize("bad", ALWAYS_REFUSED)
    def test_always_refused(self, bad, strict):
        from manifest import validate_manifest_file_name
        with pytest.raises(ValueError, match="cartridge directory"):
            validate_manifest_file_name(bad, strict=strict)

    @pytest.mark.parametrize("name", STRICT_ONLY_REFUSED)
    def test_strict_refuses_but_curated_accepts(self, name):
        from manifest import validate_manifest_file_name
        with pytest.raises(ValueError, match="cartridge directory"):
            validate_manifest_file_name(name, strict=True)
        assert validate_manifest_file_name(name, strict=False) == name

    @pytest.mark.parametrize("strict", [True, False])
    @pytest.mark.parametrize("good", ACCEPTED)
    def test_accepted(self, good, strict):
        from manifest import validate_manifest_file_name
        assert validate_manifest_file_name(good, strict=strict) == good

    # -- which cartridges are user-authored ---------------------------------

    @staticmethod
    def _curated_root(tmp_path, monkeypatch):
        root = tmp_path / "commons"
        root.mkdir()
        monkeypatch.setattr("config.Config.PROJECTS_DIR", root)
        monkeypatch.setattr("config.Config.PRIVATE_PROJECTS_DIR", root)
        return root

    def test_cartridge_outside_curated_roots_is_user_authored(self, tmp_path, monkeypatch):
        from manifest import is_user_authored
        self._curated_root(tmp_path, monkeypatch)
        (tmp_path / "user" / "c").mkdir(parents=True)
        assert is_user_authored(tmp_path / "user" / "c") is True

    def test_curated_cartridge_is_not_user_authored(self, tmp_path, monkeypatch):
        from manifest import is_user_authored
        root = self._curated_root(tmp_path, monkeypatch)
        (root / "c").mkdir()
        assert is_user_authored(root / "c") is False

    @pytest.mark.parametrize("kind", ["fork", "github"])
    def test_fork_or_import_meta_is_user_authored_even_on_a_curated_root(
        self, tmp_path, monkeypatch, kind
    ):
        from manifest import is_user_authored
        root = self._curated_root(tmp_path, monkeypatch)
        (root / "c").mkdir()
        (root / "c" / "project.meta.json").write_text(json.dumps({"source": {"type": kind}}))
        assert is_user_authored(root / "c") is True

    # -- the rule applied through a manifest ---------------------------------

    def _manifest_at(self, project_dir, modes):
        data = {
            "project": {"name": "C", "slug": project_dir.name, "version": "1.0.0"},
            "modes": modes, "parts": [{"id": "body"}], "parameters": [],
        }
        return ProjectManifest(data, project_dir)

    def test_curated_name_outside_strict_class_still_renders(self, tmp_path, monkeypatch):
        root = self._curated_root(tmp_path, monkeypatch)
        (root / "c").mkdir()
        m = self._manifest_at(root / "c", [{"id": "m", "scad_file": "My Part.scad", "parts": ["body"]}])
        assert list(m.get_allowed_files()) == ["My Part.scad"]

    def test_user_name_outside_strict_class_is_not_renderable(self, tmp_path, monkeypatch):
        self._curated_root(tmp_path, monkeypatch)
        (tmp_path / "user" / "c").mkdir(parents=True)
        m = self._manifest_at(tmp_path / "user" / "c",
                              [{"id": "m", "scad_file": "My Part.scad", "parts": ["body"]}])
        assert m.get_allowed_files() == {}

    @pytest.mark.parametrize("curated", [True, False])
    def test_newline_in_any_mode_file_field_drops_the_mode(self, tmp_path, monkeypatch, curated):
        root = self._curated_root(tmp_path, monkeypatch)
        d = (root / "c") if curated else (tmp_path / "user" / "c")
        d.mkdir(parents=True)
        modes = [
            {"id": "ok", "scad_file": "main.py", "graph_file": "main.graph.json", "parts": ["body"]},
            {"id": "s", "scad_file": "x.graph.json\nimport os", "parts": ["body"]},
            {"id": "c", "scad_file": "c.scad", "cq_file": "c.py\nimport os", "parts": ["body"]},
            {"id": "g", "scad_file": "g.py", "graph_file": "g.graph.json\nimport os", "parts": ["body"]},
        ]
        assert list(self._manifest_at(d, modes).get_allowed_files()) == ["main.py"]

    def test_graph_file_escaping_cartridge_drops_the_mode(self, tmp_path, monkeypatch):
        root = self._curated_root(tmp_path, monkeypatch)
        (root / "c").mkdir()
        m = self._manifest_at(root / "c", [
            {"id": "g", "scad_file": "g.py", "graph_file": "../other/g.graph.json", "parts": ["body"]},
        ])
        assert m.get_allowed_files() == {}

    def test_static_stl_must_qualify(self, tmp_path):
        d = _write_manifest(tmp_path, extra={
            "parts": [
                {"id": "ok", "static_stl": "parts/ok.stl"},
                {"id": "bad", "static_stl": "../../etc/passwd"},
            ],
        })
        m = ProjectManifest(json.loads((d / "project.json").read_text()), d)
        stl = m.get_static_stl_map()
        assert "ok" in stl and "bad" not in stl
