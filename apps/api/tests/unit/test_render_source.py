"""The render-source rule (services/engine/render_source.py).

User cartridges (``project.meta.json`` ``source.type`` fork or github) render a
mode's declared ``graph_file`` with the graph engine; every other cartridge —
the commons, the private cartridges, anything without a user source type —
renders the mode's ``scad_file``.
"""
import hashlib
import json
from pathlib import Path

import pytest

from manifest import ProjectManifest
from services.engine.render_source import (
    KIND_GRAPH,
    KIND_SCRIPT,
    RenderSourceError,
    cartridge_source_type,
    graph_sources,
    render_engine_for_mode,
    render_source_for_mode,
    source_content_hash,
)

GRAPH = "part.graph.json"
GRAPH_DOC = {
    "version": "1.1.0", "units": "mm",
    "nodes": [{"id": "body", "type": "box", "params": {"w": 10, "d": 10, "h": 10}}],
    "outputs": {"body": "body"},
}


def _manifest_data(*, graph_file=GRAPH, scad_file="main.py", engine=None):
    mode = {"id": "body", "scad_file": scad_file, "parts": ["body"], "label": {"en": "Body"}}
    if graph_file is not None:
        mode["graph_file"] = graph_file
    if engine:
        mode["engine"] = engine
    return {
        "project": {"slug": "twin", "name": "Twin", "engine": "cadquery"},
        "modes": [mode],
        "parts": [{"id": "body"}],
        "parameters": [{"id": "size", "type": "slider", "default": 10}],
    }


def _cartridge(root: Path, *, meta=None, data=None, graph=True) -> ProjectManifest:
    root.mkdir(parents=True, exist_ok=True)
    data = data or _manifest_data()
    (root / "project.json").write_text(json.dumps(data))
    (root / "main.py").write_text('result = cq.Workplane("XY").box(1, 1, 1)\n')
    if graph:
        (root / GRAPH).write_text(json.dumps(GRAPH_DOC))
    if meta is not None:
        (root / "project.meta.json").write_text(meta if isinstance(meta, str) else json.dumps(meta))
    return ProjectManifest(data, root)


FORK_META = {"source": {"type": "fork", "forked_from": "twin"}}
GITHUB_META = {"source": {"type": "github", "repo_url": "https://github.com/example/twin"}}


class TestRule:
    @pytest.mark.parametrize("meta", [FORK_META, GITHUB_META], ids=["fork", "github"])
    def test_user_cartridge_with_graph_renders_the_graph(self, tmp_path, meta):
        manifest = _cartridge(tmp_path / "user", meta=meta)
        source = render_source_for_mode(manifest, "body")
        assert source.kind == KIND_GRAPH
        assert source.engine == "graph"
        assert source.filename == GRAPH
        assert source.path == (tmp_path / "user" / GRAPH).resolve()

    @pytest.mark.parametrize("meta", [FORK_META, GITHUB_META], ids=["fork", "github"])
    def test_user_cartridge_without_graph_renders_the_script(self, tmp_path, meta):
        manifest = _cartridge(tmp_path / "user", meta=meta, data=_manifest_data(graph_file=None), graph=False)
        source = render_source_for_mode(manifest, "body")
        assert (source.kind, source.engine, source.filename) == (KIND_SCRIPT, "cadquery", "main.py")

    @pytest.mark.parametrize("meta", [
        None,                                   # commons: no project.meta.json
        {"source": {"type": "local"}},          # an unknown source type
        {"source": {}},                         # no type at all
        "{not json",                            # unreadable
        ["fork"],                               # not an object
    ], ids=["commons", "unknown-type", "typeless", "corrupt", "not-an-object"])
    @pytest.mark.parametrize("graph", [True, False], ids=["graph", "no-graph"])
    def test_curated_cartridge_renders_the_script(self, tmp_path, meta, graph):
        data = _manifest_data(graph_file=GRAPH if graph else None)
        manifest = _cartridge(tmp_path / "commons", meta=meta, data=data, graph=graph)
        source = render_source_for_mode(manifest, "body")
        assert (source.kind, source.engine, source.filename) == (KIND_SCRIPT, "cadquery", "main.py")
        assert source.path == tmp_path / "commons" / "main.py"

    def test_private_cartridge_renders_the_script(self, tmp_path, monkeypatch):
        from config import Config

        private_root = tmp_path / "private-projects"
        monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", private_root)
        manifest = _cartridge(private_root / "client-twin")
        assert render_source_for_mode(manifest, "body").kind == KIND_SCRIPT

    def test_graph_engine_mode_keeps_its_graph_everywhere(self, tmp_path):
        data = _manifest_data(graph_file=None, scad_file=GRAPH)
        manifest = _cartridge(tmp_path / "commons", data=data)
        source = render_source_for_mode(manifest, "body")
        assert (source.kind, source.engine, source.filename) == (KIND_SCRIPT, "graph", GRAPH)

    def test_unknown_mode(self, tmp_path):
        manifest = _cartridge(tmp_path / "user", meta=FORK_META)
        assert render_source_for_mode(manifest, "nope") is None
        assert render_engine_for_mode(manifest, "nope") == "cadquery"

    def test_engine_follows_the_source(self, tmp_path):
        fork = _cartridge(tmp_path / "fork", meta=FORK_META)
        commons = _cartridge(tmp_path / "commons")
        assert render_engine_for_mode(fork, "body") == "graph"
        assert render_engine_for_mode(commons, "body") == "cadquery"
        assert render_engine_for_mode(fork, None) == "cadquery"

    def test_source_type_reader(self, tmp_path):
        assert cartridge_source_type(tmp_path) is None
        (tmp_path / "project.meta.json").write_text(json.dumps(FORK_META))
        assert cartridge_source_type(tmp_path) == "fork"


class TestInvalidGraphInAUserCartridge:
    @pytest.mark.parametrize("name", [
        "/etc/part.graph.json",
        "../other/part.graph.json",
        "sub/../part.graph.json",
        "part.json",
        "main.py",
        "bad name.graph.json",
        "evil\nimport os.graph.json",
        "",
        42,
    ])
    def test_rejected_and_never_falls_back(self, tmp_path, name):
        manifest = _cartridge(tmp_path / "user", meta=FORK_META, data=_manifest_data(graph_file=name))
        with pytest.raises(RenderSourceError):
            render_source_for_mode(manifest, "body")
        # The engine lookup never raises; the source lookup that precedes every
        # render is what reports the error.
        assert render_engine_for_mode(manifest, "body") == "cadquery"

    def test_missing_graph(self, tmp_path):
        manifest = _cartridge(tmp_path / "user", meta=FORK_META, graph=False)
        with pytest.raises(RenderSourceError, match="does not exist"):
            render_source_for_mode(manifest, "body")

    def test_symlink_out_of_the_cartridge(self, tmp_path):
        outside = tmp_path / "outside.graph.json"
        outside.write_text(json.dumps(GRAPH_DOC))
        manifest = _cartridge(tmp_path / "user", meta=FORK_META, graph=False)
        (tmp_path / "user" / GRAPH).symlink_to(outside)
        with pytest.raises(RenderSourceError, match="inside the project"):
            render_source_for_mode(manifest, "body")

    def test_nested_plain_path_is_fine(self, tmp_path):
        data = _manifest_data(graph_file="graphs/part.graph.json")
        manifest = _cartridge(tmp_path / "user", meta=FORK_META, data=data, graph=False)
        (tmp_path / "user" / "graphs").mkdir()
        (tmp_path / "user" / "graphs" / GRAPH).write_text(json.dumps(GRAPH_DOC))
        assert render_source_for_mode(manifest, "body").filename == "graphs/part.graph.json"

    def test_curated_cartridge_ignores_an_invalid_graph_file(self, tmp_path):
        manifest = _cartridge(tmp_path / "commons", data=_manifest_data(graph_file="../x.graph.json"))
        assert render_source_for_mode(manifest, "body").filename == "main.py"


class TestSourceContentHash:
    def test_script_hash_is_unchanged(self, tmp_path):
        """A script's cache identity is the MD5 compute_scad_hash always gave it."""
        script = tmp_path / "main.scad"
        script.write_text("cube(1);")
        assert source_content_hash(script) == hashlib.md5(b"cube(1);").hexdigest()

    def test_graph_hash_moves_with_the_graph(self, tmp_path):
        graph = tmp_path / GRAPH
        graph.write_text(json.dumps(GRAPH_DOC))
        first = source_content_hash(graph)
        graph.write_text(json.dumps({**GRAPH_DOC, "meta": {"note": "edited"}}))
        assert source_content_hash(graph) != first

    def test_graph_hash_moves_with_the_bindings(self, tmp_path):
        manifest = _cartridge(tmp_path / "user", meta=FORK_META)
        graph = tmp_path / "user" / GRAPH
        unbound = source_content_hash(graph, manifest)
        assert unbound == source_content_hash(graph)  # no bindings: just the file

        manifest.parameters[0]["binding"] = "body.w"
        bound = source_content_hash(graph, manifest)
        manifest.parameters[0]["binding"] = "body.d"
        rebound = source_content_hash(graph, manifest)
        assert len({unbound, bound, rebound}) == 3

    def test_script_hash_ignores_bindings(self, tmp_path):
        manifest = _cartridge(tmp_path / "user", meta=FORK_META)
        manifest.parameters[0]["binding"] = "body.w"
        script = tmp_path / "user" / "main.py"
        assert source_content_hash(script, manifest) == hashlib.md5(script.read_bytes()).hexdigest()

    def test_unreadable(self, tmp_path):
        assert source_content_hash(tmp_path / "missing.graph.json") is None


class TestGraphSources:
    def test_user_cartridge_includes_declared_graphs(self, tmp_path):
        manifest = _cartridge(tmp_path / "user", meta=FORK_META)
        assert graph_sources(tmp_path / "user", manifest.as_json()) == [(tmp_path / "user" / GRAPH).resolve()]

    def test_curated_cartridge_lists_only_graph_engine_modes(self, tmp_path):
        manifest = _cartridge(tmp_path / "commons")
        assert graph_sources(tmp_path / "commons", manifest.as_json()) == []
        data = _manifest_data(graph_file=None, scad_file=GRAPH)
        assert graph_sources(tmp_path / "commons", data) == [(tmp_path / "commons" / GRAPH).resolve()]

    def test_paths_outside_are_skipped(self, tmp_path):
        data = _manifest_data(graph_file="../x.graph.json", scad_file="../y.graph.json")
        _cartridge(tmp_path / "user", meta=FORK_META, data=data)
        assert graph_sources(tmp_path / "user", data) == []


class TestOrchestratorUsesTheRule:
    """resolve_render_context and resolve_engine_config agree with the resolver."""

    @pytest.fixture
    def roots(self, tmp_path, monkeypatch, user_projects_dir):
        from config import Config

        commons = tmp_path / "commons"
        monkeypatch.setattr(Config, "PROJECTS_DIR", commons)
        monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [commons, user_projects_dir])
        _cartridge(commons / "twin")
        data = _manifest_data()
        data["project"]["slug"] = "my-twin"
        _cartridge(user_projects_dir / "my-twin", meta=FORK_META, data=data)
        return commons, user_projects_dir

    def test_fork_context_is_the_graph(self, roots):
        from services.engine.render_orchestrator import extract_render_payload, resolve_engine_config

        _commons, user = roots
        payload = extract_render_payload({"project": "my-twin", "mode": "body", "parameters": {}})
        assert payload["scad_filename"] == GRAPH
        assert Path(payload["scad_path"]) == (user / "my-twin" / GRAPH).resolve()
        engine, path, fmt, err = resolve_engine_config({"mode": "body"}, payload, "pro")
        assert (engine, fmt, err) == ("graph", "stl", None)
        assert Path(path) == Path(payload["scad_path"])

    def test_commons_context_is_the_script(self, roots):
        from services.engine.render_orchestrator import extract_render_payload, resolve_engine_config

        commons, _user = roots
        payload = extract_render_payload({"project": "twin", "mode": "body", "parameters": {}})
        assert payload["scad_filename"] == "main.py"
        assert Path(payload["scad_path"]) == commons / "twin" / "main.py"
        engine, _path, _fmt, err = resolve_engine_config({"mode": "body"}, payload, "pro")
        assert (engine, err) == ("cadquery", None)

    def test_fork_graph_is_gated_as_the_graph_engine(self, roots):
        from services.engine.render_orchestrator import extract_render_payload, resolve_engine_config

        payload = extract_render_payload({"project": "my-twin", "mode": "body", "parameters": {}})
        engine, _path, _fmt, err = resolve_engine_config({"mode": "body"}, payload, "guest")
        assert engine == "graph"
        assert err == ("Graph engine is not available for your tier.", 403)

    def test_mode_less_payload_uses_the_first_mode_source(self, roots):
        from services.engine.render_orchestrator import extract_render_payload, resolve_engine_config

        payload = extract_render_payload({"project": "my-twin", "parameters": {}})
        assert payload["mode"] == "body"
        assert payload["scad_filename"] == GRAPH
        engine, _path, _fmt, _err = resolve_engine_config({}, payload, "pro")
        assert engine == "graph"

    def test_invalid_fork_graph_is_a_payload_error(self, roots):
        from services.engine.render_orchestrator import RenderPayloadError, extract_render_payload

        _commons, user = roots
        (user / "my-twin" / GRAPH).unlink()
        result = extract_render_payload({"project": "my-twin", "mode": "body", "parameters": {}})
        assert isinstance(result, RenderPayloadError)
        assert "does not exist" in result.message
