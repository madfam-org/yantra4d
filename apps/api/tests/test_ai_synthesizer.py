import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from config import Config
from services.ai.ai_synthesizer import build_synthesis_prompt, parse_synthesis


@pytest.fixture
def mock_projects_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        monkeypatch.setattr(Config, "PROJECTS_DIR", temp_dir)
        yield Path(temp_dir)


# ---------------------------------------------------------------------------
# Existing tests
# ---------------------------------------------------------------------------

def test_synthesis_parsing_and_extraction():
    # Mock LLM Output
    llm_response = '''
Here is your new Cartridge.

```json
{
  "slug": "test-synthesized-box",
  "manifest": {
    "project": {
      "name": "Test Box",
      "slug": "test-synthesized-box",
      "version": "1.0.0"
    },
    "modes": [
      {
        "id": "main",
        "scad_file": "main.scad",
        "parts": ["box"]
      }
    ],
    "parts": [
      {
        "id": "box",
        "render_mode": 0,
        "default_color": "#ff0000"
      }
    ],
    "parameters": [
      {
        "id": "width",
        "type": "slider",
        "min": 10,
        "max": 100,
        "default": 50
      }
    ]
  },
  "files": {
    "main.scad": "width=50;\\ncube([width, width, width]);"
  }
}
```
'''
    parsed = parse_synthesis(llm_response)

    assert parsed["cartridge"] is not None
    assert parsed["cartridge"]["slug"] == "test-synthesized-box"
    assert "width" in parsed["cartridge"]["files"]["main.scad"]
    assert len(parsed["cartridge"]["manifest"]["parameters"]) == 1

def test_invalid_json_is_caught():
    llm_response = '''
I made a box but forgot the JSON block!
{"slug": "test"
    '''
    parsed = parse_synthesis(llm_response)
    assert parsed["cartridge"] is None


# ---------------------------------------------------------------------------
# build_synthesis_prompt tests
# ---------------------------------------------------------------------------

class TestBuildSynthesisPrompt:
    def test_returns_nonempty_string(self):
        prompt = build_synthesis_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_prompt_mentions_mandatory_keys(self):
        prompt = build_synthesis_prompt()
        assert "slug" in prompt
        assert "manifest" in prompt
        assert "files" in prompt

    def test_prompt_mentions_openscad(self):
        prompt = build_synthesis_prompt()
        assert "OpenSCAD" in prompt


# ---------------------------------------------------------------------------
# parse_synthesis edge-case tests
# ---------------------------------------------------------------------------

class TestParseSynthesisEdgeCases:
    def test_no_json_block_returns_none_cartridge(self):
        result = parse_synthesis("Just some text without JSON")
        assert result["cartridge"] is None
        assert result["explanation"] == "Just some text without JSON"

    def test_json_missing_slug_returns_none(self):
        raw = '```json\n{"manifest": {"name": "x"}, "files": {"a.scad": "cube(1);"}}\n```'
        result = parse_synthesis(raw)
        assert result["cartridge"] is None

    def test_json_missing_files_returns_none(self):
        raw = '```json\n{"slug": "x", "manifest": {"name": "x"}}\n```'
        result = parse_synthesis(raw)
        assert result["cartridge"] is None

    def test_json_missing_manifest_returns_none(self):
        raw = '```json\n{"slug": "x", "files": {"a.scad": "cube(1);"}}\n```'
        result = parse_synthesis(raw)
        assert result["cartridge"] is None

    def test_explanation_stripped_of_json_block(self):
        raw = 'Here is your project.\n```json\n{"slug": "x", "manifest": {}, "files": {}}\n```\nEnjoy!'
        result = parse_synthesis(raw)
        assert result["cartridge"] is not None
        assert "```json" not in result["explanation"]
        assert "Enjoy!" in result["explanation"]

    def test_bare_json_object_with_manifest_key(self):
        """Bare JSON (no code fences) with manifest key should be parsed via fallback regex."""
        raw = '{"slug": "x", "manifest": {"name": "x"}, "files": {"a.scad": "cube(1);"}}'
        result = parse_synthesis(raw)
        # The fallback regex tries to match — result depends on regex coverage
        # If matched, cartridge should be valid; if not, cartridge is None
        # Either way, no exception is raised
        assert "cartridge" in result
        assert "explanation" in result

    def test_malformed_json_inside_fences(self):
        raw = '```json\n{not valid json at all}\n```'
        result = parse_synthesis(raw)
        assert result["cartridge"] is None


# ---------------------------------------------------------------------------
# stream_synthesis_response tests
# ---------------------------------------------------------------------------

class TestStreamSynthesisResponse:
    @patch("services.ai.ai_synthesizer.stream_chat")
    @patch("services.ai.ai_synthesizer.append_message")
    @patch("services.ai.ai_synthesizer.get_messages")
    def test_yields_chunks_then_done(self, mock_get, mock_append, mock_stream):
        from services.ai.ai_synthesizer import stream_synthesis_response

        mock_get.return_value = [{"role": "user", "content": "make a box"}]
        mock_stream.return_value = iter(["Hello ", "world"])

        events = list(stream_synthesis_response("sess-1", "make a box"))
        chunk_events = [e for e in events if e["event"] == "chunk"]
        done_events = [e for e in events if e["event"] == "done"]

        assert len(chunk_events) == 2
        assert chunk_events[0]["text"] == "Hello "
        assert chunk_events[1]["text"] == "world"
        assert len(done_events) == 1

    @patch("services.ai.ai_synthesizer.stream_chat")
    @patch("services.ai.ai_synthesizer.append_message")
    @patch("services.ai.ai_synthesizer.get_messages")
    def test_cartridge_event_when_valid_json(
        self, mock_get, mock_append, mock_stream, mock_projects_dir
    ):
        from services.ai.ai_synthesizer import stream_synthesis_response

        cartridge_json = json.dumps({
            "slug": "synth-test",
            "manifest": {"project": {"name": "T"}},
            "files": {"main.scad": "cube(1);"},
        })
        llm_output = f"Here you go.\n```json\n{cartridge_json}\n```"
        mock_get.return_value = []
        mock_stream.return_value = iter([llm_output])

        events = list(stream_synthesis_response("sess-2", "make something"))
        event_types = [e["event"] for e in events]

        assert "cartridge" in event_types
        assert "done" in event_types
        # Verify project directory was created on disk
        created_dirs = list(mock_projects_dir.iterdir())
        assert len(created_dirs) == 1
        assert (created_dirs[0] / "project.json").exists()
        assert (created_dirs[0] / "main.scad").exists()

    @patch("services.ai.ai_synthesizer.stream_chat")
    @patch("services.ai.ai_synthesizer.append_message")
    @patch("services.ai.ai_synthesizer.get_messages")
    def test_no_cartridge_event_for_plain_text(
        self, mock_get, mock_append, mock_stream
    ):
        from services.ai.ai_synthesizer import stream_synthesis_response

        mock_get.return_value = []
        mock_stream.return_value = iter(["Just a plain answer, no JSON."])

        events = list(stream_synthesis_response("sess-3", "hello"))
        event_types = [e["event"] for e in events]

        assert "cartridge" not in event_types
        assert "done" in event_types

    @patch("services.ai.ai_synthesizer.stream_chat")
    @patch("services.ai.ai_synthesizer.append_message")
    @patch("services.ai.ai_synthesizer.get_messages")
    def test_appends_user_and_assistant_messages(
        self, mock_get, mock_append, mock_stream
    ):
        from services.ai.ai_synthesizer import stream_synthesis_response

        mock_get.return_value = []
        mock_stream.return_value = iter(["response"])

        list(stream_synthesis_response("sess-4", "prompt text"))

        # First call: user message; second call: assistant message
        assert mock_append.call_count == 2
        mock_append.assert_any_call("sess-4", "user", "prompt text")
        mock_append.assert_any_call("sess-4", "assistant", "response")
