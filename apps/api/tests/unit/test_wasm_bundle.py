"""Unit tests for the WASM bundle builder — resolution, fonts, honesty lists, ETag.

These exercise the resolver directly against a temp tree rather than through the
route, so the interesting cases (a cycle, a traversal attempt, a cap) can be
built exactly and cheaply. The route's own behaviour lives in
tests/e2e/test_wasm_bundle_api.py.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.core.scad_analyzer import extract_dependencies
from services.engine.wasm_bundle import (
    UNSUPPORTED_IMPORT,
    UNSUPPORTED_MISSING_INCLUDE,
    UNSUPPORTED_SURFACE,
    Bundle,
    BundleTooLarge,
    collect_fonts,
    compute_etag,
    confine,
    detect_unsupported,
    resolve_sources,
    strip_comments,
    uses_text,
)

SLUG = "cartridge"


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A projects dir and a libs dir, wired into Config the way the server is."""
    import os

    from config import Config

    projects = tmp_path / "projects"
    libs = tmp_path / "libs"
    dotscad = libs / "dotSCAD" / "src"
    project = projects / SLUG
    for directory in (project, libs / "BOSL2", dotscad):
        directory.mkdir(parents=True)

    monkeypatch.setattr(Config, "PROJECTS_DIR", projects)
    monkeypatch.setattr(Config, "LIBS_DIR", libs)
    monkeypatch.setattr(Config, "FONTS_DIR", tmp_path / "shared-fonts")
    monkeypatch.setattr(
        Config, "OPENSCADPATH",
        os.pathsep.join([str(libs), str(dotscad), str(projects)]),
    )
    return {"root": tmp_path, "projects": projects, "libs": libs,
            "dotscad": dotscad, "project": project}


def _entry(tree, name="main.scad", body="cube(10);\n"):
    path = tree["project"] / name
    path.write_text(body)
    return path


class TestRelativeResolution:
    def test_sibling_include(self, tree):
        _entry(tree, "main.scad", "include <helper.scad>\ncube(1);\n")
        (tree["project"] / "helper.scad").write_text("module helper(){}\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert set(files) == {f"projects/{SLUG}/main.scad", f"projects/{SLUG}/helper.scad"}
        assert unresolved == []

    def test_subdirectory_include(self, tree):
        (tree["project"] / "parts").mkdir()
        (tree["project"] / "parts" / "lid.scad").write_text("// lid\n")
        _entry(tree, "main.scad", "use <parts/lid.scad>\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert f"projects/{SLUG}/parts/lid.scad" in files
        assert unresolved == []

    def test_relative_escape_into_libs_is_the_real_world_case(self, tree):
        """`include <../../libs/BOSL2/std.scad>` — how nearly every cartridge does it."""
        (tree["libs"] / "BOSL2" / "std.scad").write_text("// BOSL2\n")
        _entry(tree, "main.scad", "include <../../libs/BOSL2/std.scad>\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert "libs/BOSL2/std.scad" in files
        assert unresolved == []

    def test_relative_beats_openscadpath(self, tree):
        """OpenSCAD looks next to the including file first; so do we."""
        (tree["project"] / "shared.scad").write_text("// local wins\n")
        (tree["libs"] / "shared.scad").write_text("// library loses\n")
        _entry(tree, "main.scad", "include <shared.scad>\n")

        files, _, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert files[f"projects/{SLUG}/shared.scad"] == "// local wins\n"
        assert "libs/shared.scad" not in files


class TestOpenscadpathFallback:
    def test_libs_root_entry(self, tree):
        (tree["libs"] / "BOSL2" / "std.scad").write_text("// BOSL2\n")
        _entry(tree, "main.scad", "include <BOSL2/std.scad>\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert "libs/BOSL2/std.scad" in files
        assert unresolved == []

    def test_dotscad_src_entry(self, tree):
        (tree["dotscad"] / "shape_taiwan.scad").write_text("// dotSCAD\n")
        _entry(tree, "main.scad", "use <shape_taiwan.scad>\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert "libs/dotSCAD/src/shape_taiwan.scad" in files
        assert unresolved == []

    def test_projects_dir_entry_is_another_cartridge_and_is_refused(self, tree):
        """PROJECTS_DIR is on OPENSCADPATH, but a bundle never carries someone else's source."""
        other = tree["projects"] / "other-cartridge"
        other.mkdir()
        (other / "shared.scad").write_text("// not ours\n")
        _entry(tree, "main.scad", "include <other-cartridge/shared.scad>\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert list(files) == [f"projects/{SLUG}/main.scad"]
        assert unresolved == [f"projects/{SLUG}/main.scad: other-cartridge/shared.scad"]


class TestRecursion:
    def test_transitive_closure(self, tree):
        (tree["libs"] / "BOSL2" / "std.scad").write_text("include <math.scad>\ninclude <paths.scad>\n")
        (tree["libs"] / "BOSL2" / "math.scad").write_text("include <constants.scad>\n")
        (tree["libs"] / "BOSL2" / "paths.scad").write_text("include <constants.scad>\n")
        (tree["libs"] / "BOSL2" / "constants.scad").write_text("PI2 = 6.28;\n")
        _entry(tree, "main.scad", "include <../../libs/BOSL2/std.scad>\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert set(files) == {
            f"projects/{SLUG}/main.scad",
            "libs/BOSL2/std.scad", "libs/BOSL2/math.scad",
            "libs/BOSL2/paths.scad", "libs/BOSL2/constants.scad",
        }
        assert unresolved == []

    def test_cycle_terminates(self, tree):
        _entry(tree, "a.scad", "include <b.scad>\n")
        (tree["project"] / "b.scad").write_text("include <a.scad>\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "a.scad"], tree["project"])

        assert set(files) == {f"projects/{SLUG}/a.scad", f"projects/{SLUG}/b.scad"}
        assert unresolved == []

    def test_self_include_terminates(self, tree):
        _entry(tree, "a.scad", "include <a.scad>\n")

        files, _, _ = resolve_sources([tree["project"] / "a.scad"], tree["project"])

        assert list(files) == [f"projects/{SLUG}/a.scad"]


class TestConfinement:
    def test_traversal_out_of_every_root_is_refused(self, tree):
        secret = tree["root"] / "secret.scad"
        secret.write_text("// never\n")
        _entry(tree, "main.scad", "include <../../secret.scad>\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert list(files) == [f"projects/{SLUG}/main.scad"]
        assert unresolved == [f"projects/{SLUG}/main.scad: ../../secret.scad"]

    def test_absolute_path_outside_the_roots_is_refused(self, tree):
        _entry(tree, "main.scad", "include </etc/passwd>\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert list(files) == [f"projects/{SLUG}/main.scad"]
        assert unresolved == [f"projects/{SLUG}/main.scad: /etc/passwd"]

    def test_symlink_pointing_out_of_the_tree_is_refused(self, tree):
        outside = tree["root"] / "outside.scad"
        outside.write_text("// never\n")
        (tree["project"] / "linked.scad").symlink_to(outside)
        _entry(tree, "main.scad", "include <linked.scad>\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert list(files) == [f"projects/{SLUG}/main.scad"]
        assert unresolved == [f"projects/{SLUG}/main.scad: linked.scad"]

    def test_confine_maps_a_libs_path_to_its_virtual_path(self, tree):
        roots = [(f"projects/{SLUG}", tree["project"]), ("libs", tree["libs"])]

        placed = confine(tree["libs"] / "BOSL2" / "std.scad", roots)

        assert placed is not None
        assert placed[0] == "libs/BOSL2/std.scad"

    def test_confine_refuses_a_path_under_no_root(self, tree):
        roots = [(f"projects/{SLUG}", tree["project"]), ("libs", tree["libs"])]

        assert confine(tree["root"] / "elsewhere.scad", roots) is None


class TestUnresolved:
    def test_missing_include_is_recorded_with_its_including_file(self, tree):
        _entry(tree, "main.scad", "include <ghost.scad>\nuse <also-ghost.scad>\n")

        files, unresolved, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert list(files) == [f"projects/{SLUG}/main.scad"]
        assert unresolved == [
            f"projects/{SLUG}/main.scad: ghost.scad",
            f"projects/{SLUG}/main.scad: also-ghost.scad",
        ]

    def test_missing_entry_file_is_recorded(self, tree):
        files, unresolved, _ = resolve_sources(
            [tree["project"] / "absent.scad"], tree["project"],
        )

        assert files == {}
        assert unresolved == [f"projects/{SLUG}/absent.scad"]


class TestSizeCaps:
    def test_byte_cap(self, tree, monkeypatch):
        import services.engine.wasm_bundle as mod
        monkeypatch.setattr(mod, "MAX_BUNDLE_BYTES", 1024)
        _entry(tree, "main.scad", "x = 1;\n" + ("// filler\n" * 500))

        with pytest.raises(BundleTooLarge) as excinfo:
            resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert excinfo.value.bytes > 1024
        assert excinfo.value.files == 1

    def test_file_count_cap(self, tree, monkeypatch):
        import services.engine.wasm_bundle as mod
        monkeypatch.setattr(mod, "MAX_BUNDLE_FILES", 3)
        includes = "".join(f"include <part{i}.scad>\n" for i in range(10))
        _entry(tree, "main.scad", includes)
        for i in range(10):
            (tree["project"] / f"part{i}.scad").write_text(f"// {i}\n")

        with pytest.raises(BundleTooLarge) as excinfo:
            resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert excinfo.value.files > 3
        assert excinfo.value.max_files == 3

    def test_a_single_oversized_file_trips_before_it_is_read(self, tree, monkeypatch):
        """The cap must stop a pathological file, not survive reading it."""
        import services.engine.wasm_bundle as mod
        monkeypatch.setattr(mod, "MAX_BUNDLE_BYTES", 64)
        monkeypatch.setattr(
            mod, "_read_text",
            lambda path: pytest.fail("an oversized file must never be read into memory"),
        )
        _entry(tree, "main.scad", "x" * 4096)

        with pytest.raises(BundleTooLarge):
            resolve_sources([tree["project"] / "main.scad"], tree["project"])

    def test_under_the_cap_is_untouched(self, tree):
        _entry(tree, "main.scad", "cube(1);\n")

        files, _, _ = resolve_sources([tree["project"] / "main.scad"], tree["project"])

        assert len(files) == 1


class TestFonts:
    def _shared_font(self, tree, name="Shared.ttf"):
        shared = tree["root"] / "shared-fonts"
        shared.mkdir(exist_ok=True)
        (shared / name).write_bytes(b"\x00\x01ttf-shared")
        return shared

    def test_cartridge_fonts_always_travel(self, tree):
        (tree["project"] / "fonts").mkdir()
        (tree["project"] / "fonts" / "Local.otf").write_bytes(b"otf-bytes")

        fonts, raw_bytes, _ = collect_fonts(tree["project"], {"a.scad": "cube(1);"})

        assert f"projects/{SLUG}/fonts/Local.otf" in fonts
        assert raw_bytes == len(b"otf-bytes") + len(fonts["fonts.conf"].encode())

    def test_cartridge_font_is_base64(self, tree):
        import base64
        (tree["project"] / "fonts").mkdir()
        (tree["project"] / "fonts" / "Local.ttf").write_bytes(b"\x00\x01\x02raw")

        fonts, _, _ = collect_fonts(tree["project"], {})

        decoded = base64.b64decode(fonts[f"projects/{SLUG}/fonts/Local.ttf"])
        assert decoded == b"\x00\x01\x02raw"

    def test_shared_fonts_only_when_a_source_calls_text(self, tree):
        self._shared_font(tree)

        without, _, _ = collect_fonts(tree["project"], {"a.scad": "cube(10);\n"})
        with_text, _, _ = collect_fonts(tree["project"], {"a.scad": 'text("hi");\n'})

        assert without == {}
        assert "fonts/Shared.ttf" in with_text

    def test_fonts_conf_lists_every_directory(self, tree):
        self._shared_font(tree)
        (tree["project"] / "fonts").mkdir()
        (tree["project"] / "fonts" / "Local.ttf").write_bytes(b"ttf")

        fonts, _, _ = collect_fonts(tree["project"], {"a.scad": 'text("hi");'})

        conf = fonts["fonts.conf"]
        assert f"<dir>/projects/{SLUG}/fonts</dir>" in conf
        assert "<dir>/fonts</dir>" in conf
        assert conf.startswith('<?xml version="1.0"?>')

    def test_no_fonts_means_no_fonts_conf(self, tree):
        fonts, raw_bytes, _ = collect_fonts(tree["project"], {"a.scad": 'text("hi");'})

        assert fonts == {}
        assert raw_bytes == 0

    def test_non_font_files_are_ignored(self, tree):
        (tree["project"] / "fonts").mkdir()
        (tree["project"] / "fonts" / "README.md").write_text("not a font")

        fonts, _, _ = collect_fonts(tree["project"], {})

        assert fonts == {}

    @pytest.mark.parametrize("source,expected", [
        ('text("hi");', True),
        ("text ( \"hi\" );", True),
        ("linear_extrude(2) text(msg);", True),
        ("cube(10);", False),
        ("mytext(1);", False),
        ("$text(1);", False),
    ])
    def test_text_detection(self, source, expected):
        assert uses_text({"a.scad": source}) is expected

    def test_fontconfig_generator_is_the_one_the_native_binary_uses(self):
        from services.engine.openscad import fontconfig_xml

        assert "<dir>/a</dir>\n  <dir>/b</dir>" in fontconfig_xml(["/a", "/b"])


class TestUnsupported:
    def test_import_is_flagged(self):
        found = detect_unsupported({"a.scad": 'import("part.stl");'}, [])

        assert found == [UNSUPPORTED_IMPORT]

    def test_surface_is_flagged(self):
        found = detect_unsupported({"a.scad": 'surface(file="height.dat");'}, [])

        assert found == [UNSUPPORTED_SURFACE]

    def test_unresolved_include_is_flagged(self):
        found = detect_unsupported({"a.scad": "cube(1);"}, ["a.scad: ghost.scad"])

        assert found == [UNSUPPORTED_MISSING_INCLUDE]

    def test_clean_source_flags_nothing(self):
        assert detect_unsupported({"a.scad": "cube(10);\nsphere(2);\n"}, []) == []

    def test_commented_out_features_are_not_flagged(self):
        source = "// import(\"old.stl\");\n/* surface(file=\"h.dat\"); */\ncube(1);\n"

        assert detect_unsupported({"a.scad": source}, []) == []

    def test_a_word_ending_in_import_is_not_import(self):
        assert detect_unsupported({"a.scad": "module reimport(x) { cube(x); }\nreimport(1);"}, []) == []

    def test_every_finding_is_reported_once(self):
        files = {"a.scad": 'import("x.stl");', "b.scad": 'import("y.stl"); surface(file="h");'}

        assert detect_unsupported(files, []) == [UNSUPPORTED_IMPORT, UNSUPPORTED_SURFACE]


class TestStripComments:
    def test_line_comment(self):
        assert "gone" not in strip_comments("cube(1); // gone\n")

    def test_block_comment(self):
        assert "gone" not in strip_comments("cube(1); /* gone */ sphere(2);")

    def test_string_containing_slashes_survives(self):
        stripped = strip_comments('msg = "http://example.com"; import("x.stl");')

        assert "import(" in stripped

    def test_unterminated_block_comment_swallows_the_rest(self):
        assert "cube" not in strip_comments("/* open\ncube(1);")

    def test_line_structure_is_preserved(self):
        stripped = strip_comments("include <a.scad> // note\ninclude <b.scad>\n")

        assert extract_dependencies(stripped) == ["a.scad", "b.scad"]


class TestExtractDependencies:
    def test_includes_and_uses_in_source_order(self):
        text = "use <b.scad>\ninclude <a.scad>\nuse <c.scad>\n"

        assert extract_dependencies(text) == ["b.scad", "a.scad", "c.scad"]

    def test_duplicates_collapse(self):
        text = "include <a.scad>\nuse <a.scad>\n"

        assert extract_dependencies(text) == ["a.scad"]

    def test_indented_include_is_found(self):
        assert extract_dependencies("    include <a.scad>\n") == ["a.scad"]

    def test_commented_include_is_not_a_dependency(self):
        assert extract_dependencies("// include <a.scad>\n") == []


class TestEtag:
    def _bundle(self, **overrides):
        base = {
            "slug": SLUG, "engine": "openscad", "entry_files": ["main.scad"],
            "files": {f"projects/{SLUG}/main.scad": "cube(10);\n"},
            "fonts": {}, "unsupported": [], "unresolved": [], "bytes": 10,
        }
        base.update(overrides)
        return Bundle(**base)

    def test_is_stable_across_calls(self):
        assert compute_etag(self._bundle()) == compute_etag(self._bundle())

    def test_is_stable_across_file_insertion_order(self):
        a = self._bundle(files={"projects/x/a.scad": "1", "projects/x/b.scad": "2"})
        b = self._bundle(files={"projects/x/b.scad": "2", "projects/x/a.scad": "1"})

        assert compute_etag(a) == compute_etag(b)

    def test_changes_when_a_source_changes(self):
        changed = self._bundle(files={f"projects/{SLUG}/main.scad": "cube(11);\n"})

        assert compute_etag(self._bundle()) != compute_etag(changed)

    def test_changes_when_a_file_is_added(self):
        more = self._bundle(files={
            f"projects/{SLUG}/main.scad": "cube(10);\n",
            "libs/BOSL2/std.scad": "// lib\n",
        })

        assert compute_etag(self._bundle()) != compute_etag(more)

    def test_changes_when_a_font_is_added(self):
        with_font = self._bundle(fonts={"fonts/A.ttf": "AAAA"})

        assert compute_etag(self._bundle()) != compute_etag(with_font)

    def test_changes_when_an_include_breaks(self):
        broken = self._bundle(
            unresolved=["main.scad: ghost.scad"],
            unsupported=[UNSUPPORTED_MISSING_INCLUDE],
        )

        assert compute_etag(self._bundle()) != compute_etag(broken)

    def test_is_a_sha256_hex_digest(self):
        etag = compute_etag(self._bundle())

        assert len(etag) == 64
        assert all(c in "0123456789abcdef" for c in etag)
