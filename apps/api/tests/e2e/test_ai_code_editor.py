"""Tests for AI code editor service (prompt building + edit parsing)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ai.ai_code_editor import build_code_editor_prompt, parse_edits


SAMPLE_MANIFEST = {
    "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test Project"},
    "parameters": [
        {"id": "width", "label": "Width", "type": "number"},
    ],
}

SAMPLE_FILES = {
    "main.scad": "cube([$width, 10, 5]);\nsphere(r=3);",
    "helper.scad": "module base() { cube(10); }",
}


class TestBuildCodeEditorPrompt:
    def test_contains_file_contents(self):
        prompt = build_code_editor_prompt(SAMPLE_MANIFEST, SAMPLE_FILES)
        assert "main.scad" in prompt
        assert "cube([$width, 10, 5]);" in prompt
        assert "helper.scad" in prompt
        assert "module base()" in prompt

    def test_contains_parameters(self):
        prompt = build_code_editor_prompt(SAMPLE_MANIFEST, SAMPLE_FILES)
        assert "$width" in prompt


class TestParseEdits:
    def test_extracts_valid_edits(self):
        raw = 'Explanation.\n\n```json\n{"edits": [{"file": "main.scad", "search": "sphere(r=3);", "replace": "sphere(r=5);"}]}\n```'
        result = parse_edits(raw, SAMPLE_FILES)
        assert len(result["edits"]) == 1
        assert result["edits"][0]["file"] == "main.scad"
        assert result["edits"][0]["search"] == "sphere(r=3);"
        assert result["edits"][0]["replace"] == "sphere(r=5);"

    def test_ignores_unknown_file(self):
        raw = '```json\n{"edits": [{"file": "missing.scad", "search": "x", "replace": "y"}]}\n```'
        result = parse_edits(raw, SAMPLE_FILES)
        assert len(result["edits"]) == 0

    def test_ignores_unmatched_search(self):
        raw = '```json\n{"edits": [{"file": "main.scad", "search": "not_in_file", "replace": "y"}]}\n```'
        result = parse_edits(raw, SAMPLE_FILES)
        assert len(result["edits"]) == 0

    def test_no_json_returns_empty(self):
        raw = "I don't think any changes are needed."
        result = parse_edits(raw, SAMPLE_FILES)
        assert result["edits"] == []
        assert result["explanation"] == raw

    def test_multiple_edits(self):
        raw = '```json\n{"edits": [{"file": "main.scad", "search": "sphere(r=3);", "replace": "sphere(r=5);"}, {"file": "helper.scad", "search": "cube(10);", "replace": "cube(20);"}]}\n```'
        result = parse_edits(raw, SAMPLE_FILES)
        assert len(result["edits"]) == 2
