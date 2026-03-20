"""
AI Integration Tests — real LLM calls for regression detection.

Gated by AI_API_KEY env var. Uses Haiku for cost efficiency (~$0.05/run).
Assertions are structural (not string equality) for determinism.

Run: AI_API_KEY=sk-ant-... pytest tests/integration/test_ai_integration.py -v
"""
import json
import os

import pytest

AI_API_KEY = os.getenv("AI_API_KEY")
pytestmark = pytest.mark.skipif(
    not AI_API_KEY,
    reason="AI_API_KEY not set — skipping AI integration tests",
)


@pytest.fixture(scope="module")
def ai_client():
    """Create an Anthropic client for testing."""
    import anthropic
    return anthropic.Anthropic(api_key=AI_API_KEY)


class TestAIConfigurator:
    """Test the AI configurator's ability to adjust parameters from NL input."""

    def test_make_it_taller(self, ai_client):
        """AI should increase the height parameter when asked to 'make it taller'."""
        system_prompt = (
            "You are a parametric 3D model configurator. "
            "Given parameter values and a user request, return ONLY a JSON object "
            "with the parameters to change. No explanation, just JSON."
        )
        user_message = (
            "Current parameters:\n"
            "- height: 50 (min: 10, max: 200, unit: mm)\n"
            "- width: 30 (min: 10, max: 100, unit: mm)\n"
            "- wall_thickness: 2 (min: 0.8, max: 5, unit: mm)\n\n"
            'User request: "make it taller"'
        )

        response = ai_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        text = response.content[0].text.strip()

        # Extract JSON from response (may be wrapped in markdown code block)
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)
        assert isinstance(result, dict), "Response should be a JSON object"
        assert "height" in result, "Response should include 'height' parameter"
        assert result["height"] > 50, "Height should be increased from 50"
        assert result["height"] <= 200, "Height should respect max constraint"

    def test_make_walls_thinner(self, ai_client):
        """AI should decrease wall_thickness when asked for thinner walls."""
        system_prompt = (
            "You are a parametric 3D model configurator. "
            "Given parameter values and a user request, return ONLY a JSON object "
            "with the parameters to change. No explanation, just JSON."
        )
        user_message = (
            "Current parameters:\n"
            "- height: 50 (min: 10, max: 200, unit: mm)\n"
            "- width: 30 (min: 10, max: 100, unit: mm)\n"
            "- wall_thickness: 2 (min: 0.8, max: 5, unit: mm)\n\n"
            'User request: "make the walls thinner"'
        )

        response = ai_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        text = response.content[0].text.strip()

        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)
        assert isinstance(result, dict)
        assert "wall_thickness" in result
        assert result["wall_thickness"] < 2, "Wall thickness should decrease"
        assert result["wall_thickness"] >= 0.8, "Should respect min constraint"


class TestAICodeEditor:
    """Test the AI code editor's ability to generate SCAD edits from NL input."""

    def test_add_chamfer(self, ai_client):
        """AI should generate valid search/replace edits for adding a chamfer."""
        system_prompt = (
            "You are an OpenSCAD code editor. Given SCAD code and a user request, "
            "return a JSON array of search/replace edits. "
            'Format: [{"search": "original", "replace": "new"}]. '
            "Return ONLY the JSON array, no explanation."
        )
        scad_code = (
            "module box(width, height, depth) {\n"
            "    cube([width, height, depth]);\n"
            "}\n\n"
            "box(30, 50, 20);\n"
        )
        user_message = f"Current code:\n```scad\n{scad_code}```\n\nAdd a chamfer to the box edges."

        response = ai_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        text = response.content[0].text.strip()

        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)
        assert isinstance(result, list), "Response should be a JSON array"
        assert len(result) > 0, "Should have at least one edit"
        for edit in result:
            assert "search" in edit, "Each edit needs a 'search' field"
            assert "replace" in edit, "Each edit needs a 'replace' field"
            assert isinstance(edit["search"], str)
            assert isinstance(edit["replace"], str)
            assert edit["replace"] != edit["search"], "Replace should differ from search"
