"""Tests for AI configurator service (prompt building + response parsing)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ai.ai_configurator import build_configurator_prompt, parse_response


SAMPLE_MANIFEST = {
    "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test Project"},
    "parameters": [
        {"id": "width", "label": "Width", "type": "number", "min": 10, "max": 100, "step": 5, "default": 50},
        {"id": "height", "label": "Height", "type": "number", "min": 5, "max": 200, "default": 30},
        {"id": "rounded", "label": "Rounded", "type": "boolean", "default": False},
    ],
}


class TestBuildConfiguratorPrompt:
    def test_contains_param_info(self):
        prompt = build_configurator_prompt(SAMPLE_MANIFEST, {"width": 60})
        assert "width" in prompt
        assert "min=10" in prompt
        assert "max=100" in prompt
        assert "current=60" in prompt

    def test_contains_project_name(self):
        prompt = build_configurator_prompt(SAMPLE_MANIFEST, {})
        assert "Test Project" in prompt


class TestParseResponse:
    def test_extracts_json_from_code_fence(self):
        raw = 'Here is the change:\n\n```json\n{"parameter_changes": {"width": 75}}\n```\n\nDone.'
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert result["parameter_changes"] == {"width": 75}
        assert "Done." in result["explanation"]
        assert "```" not in result["explanation"]

    def test_clamps_to_min_max(self):
        raw = '```json\n{"parameter_changes": {"width": 999}}\n```'
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert result["parameter_changes"]["width"] == 100  # clamped to max

    def test_clamps_to_min(self):
        raw = '```json\n{"parameter_changes": {"width": -5}}\n```'
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert result["parameter_changes"]["width"] == 10  # clamped to min

    def test_snaps_to_step(self):
        raw = '```json\n{"parameter_changes": {"width": 53}}\n```'
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert result["parameter_changes"]["width"] == 55  # snapped to step=5

    def test_ignores_unknown_params(self):
        raw = '```json\n{"parameter_changes": {"unknown_param": 42, "width": 50}}\n```'
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert "unknown_param" not in result["parameter_changes"]
        assert result["parameter_changes"]["width"] == 50

    def test_handles_boolean_param(self):
        raw = '```json\n{"parameter_changes": {"rounded": true}}\n```'
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert result["parameter_changes"]["rounded"] is True

    def test_no_json_returns_empty_changes(self):
        raw = "I can't make any changes to that."
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert result["parameter_changes"] == {}
        assert result["explanation"] == raw

    def test_preset_values_key(self):
        raw = '```json\n{"preset_values": {"width": 80, "height": 100}, "preset_name": "Large"}\n```'
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert result["parameter_changes"]["width"] == 80
        assert result["parameter_changes"]["height"] == 100
        assert result["preset_name"] == "Large"

    def test_invalid_value_type_skipped(self):
        """Non-numeric value for a number param is silently skipped."""
        raw = '```json\n{"parameter_changes": {"width": "not_a_number"}}\n```'
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert "width" not in result["parameter_changes"]

    def test_multiple_params_in_one_response(self):
        """Multiple parameter changes in a single response are all validated."""
        raw = '```json\n{"parameter_changes": {"width": 75, "height": 150, "rounded": true}}\n```'
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert result["parameter_changes"]["width"] == 75
        assert result["parameter_changes"]["height"] == 150
        assert result["parameter_changes"]["rounded"] is True

    def test_step_snapping_with_non_zero_min(self):
        """Step snapping respects min as base: width min=10, step=5, value=62 -> 60."""
        raw = '```json\n{"parameter_changes": {"width": 62}}\n```'
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert result["parameter_changes"]["width"] == 60

    def test_malformed_json_returns_empty(self):
        """Malformed JSON returns empty changes with raw text as explanation."""
        raw = '```json\n{parameter_changes: broken}\n```'
        result = parse_response(raw, SAMPLE_MANIFEST)
        assert result["parameter_changes"] == {}

    def test_json_without_code_fence_not_matched(self):
        """Inline JSON without code fences may not be matched by the narrow regex fallback.
        The regex requires the JSON object to have no nested braces, so only simple
        structures are captured. Complex inline JSON falls back to empty changes."""
        raw = '{"parameter_changes": {"width": 50}}'
        result = parse_response(raw, SAMPLE_MANIFEST)
        # The regex `\{[^{}]*\"parameter_changes\"[^{}]*\}` cannot match nested braces
        # so this returns empty changes — testing the fallback branch
        assert result["parameter_changes"] == {}
        assert result["explanation"] == raw


class TestBuildConfiguratorPromptEdgeCases:
    def test_no_parameters_manifest(self):
        """Manifest with no parameters shows placeholder text."""
        manifest = {"project": {"name": "Empty"}, "parameters": []}
        prompt = build_configurator_prompt(manifest, {})
        assert "(no parameters)" in prompt

    def test_param_with_description(self):
        """Parameter with a description field includes it in prompt."""
        manifest = {
            "project": {"name": "Test"},
            "parameters": [
                {"id": "size", "label": "Size", "type": "number", "description": "Overall size in mm"},
            ],
        }
        prompt = build_configurator_prompt(manifest, {})
        assert "Overall size in mm" in prompt

    def test_current_params_override_default(self):
        """Current param value is shown instead of default."""
        prompt = build_configurator_prompt(SAMPLE_MANIFEST, {"width": 99})
        assert "current=99" in prompt
