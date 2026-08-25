"""
Editor API tests for graph documents.

The editor accepts `.graph.json` alongside `.scad`, and refuses to save a graph
the transpiler would reject — a dangling input or a cycle is reported while the
author is still in the editor rather than at render time.
"""
import json

import pytest

from routes.editor.editor import _graph_rejection, _validate_filepath


def valid_graph():
    return {
        "version": "1.0.0",
        "nodes": [
            {"id": "base", "type": "box", "params": {"w": 40, "d": 20, "h": 8}},
            {"id": "bore", "type": "cylinder", "params": {"r": 3, "h": 40}},
            {"id": "body", "type": "cut", "inputs": {"a": "base", "b": "bore"}},
        ],
        "outputs": {"part": "body"},
    }


class TestAcceptedPaths:
    @pytest.mark.parametrize("name", ["main.scad", "part.graph.json", "nested/part.graph.json"])
    def test_accepted(self, tmp_path, name):
        (tmp_path / "nested").mkdir(exist_ok=True)
        assert _validate_filepath(tmp_path, name) is not None

    @pytest.mark.parametrize(
        "name",
        [
            "project.json",        # a manifest is not editor-owned
            "data.json",           # a bare .json must stay rejected
            "main.py",             # cadquery scripts are not edited here
            "notes.txt",
            "../escape.graph.json",
        ],
    )
    def test_rejected(self, tmp_path, name):
        assert _validate_filepath(tmp_path, name) is None

    def test_graph_suffix_is_matched_on_the_full_chain(self, tmp_path):
        # Path.suffix is ".json" for both of these; only one may be edited.
        assert _validate_filepath(tmp_path, "a.graph.json") is not None
        assert _validate_filepath(tmp_path, "a.json") is None


class TestGraphValidationOnSave:
    def _reject(self, tmp_path, document, name="part.graph.json"):
        return _graph_rejection(tmp_path / name, json.dumps(document))

    def test_valid_graph_is_accepted(self, tmp_path):
        assert self._reject(tmp_path, valid_graph()) is None

    def test_scad_files_are_not_graph_checked(self, tmp_path):
        assert _graph_rejection(tmp_path / "main.scad", "cube([1,1,1]);") is None

    def test_malformed_json_is_explained(self, tmp_path):
        assert "not valid JSON" in _graph_rejection(tmp_path / "p.graph.json", "{nope")

    def test_dangling_input_is_reported(self, tmp_path):
        doc = valid_graph()
        doc["nodes"][2]["inputs"]["b"] = "ghost"
        assert "ghost" in self._reject(tmp_path, doc)

    def test_cycle_is_reported(self, tmp_path):
        doc = {
            "version": "1.0.0",
            "nodes": [
                {"id": "a", "type": "translate", "inputs": {"shape": "b"}},
                {"id": "b", "type": "translate", "inputs": {"shape": "a"}},
            ],
            "outputs": {"part": "a"},
        }
        assert "cycle" in self._reject(tmp_path, doc)

    def test_unknown_node_type_is_reported(self, tmp_path):
        doc = valid_graph()
        doc["nodes"][0]["type"] = "loft"
        assert "unknown node type" in self._reject(tmp_path, doc).lower()

    def test_profile_output_is_reported(self, tmp_path):
        doc = {
            "version": "1.0.0",
            "nodes": [{"id": "p", "type": "profile_rect", "params": {}}],
            "outputs": {"part": "p"},
        }
        assert "extrude" in self._reject(tmp_path, doc)

    def test_bad_version_is_reported(self, tmp_path):
        doc = valid_graph()
        doc["version"] = "2.0.0"
        assert "version" in self._reject(tmp_path, doc).lower()

    def test_selector_injection_is_refused(self, tmp_path):
        doc = valid_graph()
        doc["nodes"].append(
            {
                "id": "f",
                "type": "fillet",
                "inputs": {"shape": "body"},
                "params": {"edges": '"); import os  # ', "radius": 1},
            }
        )
        doc["outputs"]["part"] = "f"
        assert "selector" in self._reject(tmp_path, doc)
