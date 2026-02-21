"""
Unit tests for assembly_generator.py
"""
from services.core.assembly_generator import (
    generate_assembly_steps,
    merge_assembly_steps,
    _topological_sort,
    _build_attachment_graph,
)


# --- Fixtures ---

SIMPLE_MANIFEST = {
    "parts": [
        {"id": "base", "label": {"en": "Base", "es": "Base"}, "default_color": "#e5e7eb"},
        {"id": "top", "label": {"en": "Top", "es": "Superior"}, "default_color": "#3b82f6"},
    ],
    "assembly_steps": [],
}

SIMPLE_ANALYSIS = {
    "files": {
        "base.scad": {
            "attachments": [],
            "modules": [],
            "variables": [],
            "includes": [],
            "uses": [],
            "render_modes": [],
            "module_calls": [],
        },
        "top.scad": {
            "attachments": [
                {"type": "attach", "anchor": "TOP", "parent_anchor": "BOTTOM", "child": "base"},
            ],
            "modules": [],
            "variables": [],
            "includes": [],
            "uses": [],
            "render_modes": [],
            "module_calls": [],
        },
    }
}


# --- Tests ---

class TestTopologicalSort:
    def test_empty_graph(self):
        assert _topological_sort({}) == []

    def test_linear_chain(self):
        graph = {
            "a": [{"child": "b", "anchor": "TOP", "parent_anchor": "TOP"}],
            "b": [{"child": "c", "anchor": "TOP", "parent_anchor": "TOP"}],
            "c": [],
        }
        order = _topological_sort(graph)
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_no_dependencies(self):
        graph = {"a": [], "b": [], "c": []}
        order = _topological_sort(graph)
        assert set(order) == {"a", "b", "c"}

    def test_cycle_handled_gracefully(self):
        # Cycle: a→b, b→a — should not raise, just return all nodes
        graph = {
            "a": [{"child": "b", "anchor": "TOP", "parent_anchor": "TOP"}],
            "b": [{"child": "a", "anchor": "TOP", "parent_anchor": "TOP"}],
        }
        order = _topological_sort(graph)
        assert set(order) == {"a", "b"}


class TestBuildAttachmentGraph:
    def test_empty_analysis(self):
        graph = _build_attachment_graph({"files": {}}, SIMPLE_MANIFEST["parts"])
        assert graph == {}

    def test_single_attachment(self):
        graph = _build_attachment_graph(SIMPLE_ANALYSIS, SIMPLE_MANIFEST["parts"])
        assert "top" in graph
        assert any(d["child"] == "base" for d in graph["top"])


class TestGenerateAssemblySteps:
    def test_returns_list(self):
        steps = generate_assembly_steps(SIMPLE_MANIFEST, SIMPLE_ANALYSIS)
        assert isinstance(steps, list)

    def test_steps_have_required_fields(self):
        steps = generate_assembly_steps(SIMPLE_MANIFEST, SIMPLE_ANALYSIS)
        for step in steps:
            assert "step" in step
            assert "label" in step
            assert "visible_parts" in step
            assert "highlight_parts" in step
            assert "camera" in step

    def test_step_numbers_are_sequential(self):
        steps = generate_assembly_steps(SIMPLE_MANIFEST, SIMPLE_ANALYSIS)
        for i, step in enumerate(steps, start=1):
            assert step["step"] == i

    def test_auto_generated_flag(self):
        steps = generate_assembly_steps(SIMPLE_MANIFEST, SIMPLE_ANALYSIS)
        for step in steps:
            assert step.get("_auto_generated") is True

    def test_empty_manifest_parts(self):
        manifest = {"parts": [], "assembly_steps": []}
        steps = generate_assembly_steps(manifest, SIMPLE_ANALYSIS)
        assert isinstance(steps, list)


class TestMergeAssemblySteps:
    def test_empty_existing_returns_generated(self):
        generated = [{"step": 1, "label": {"en": "A"}, "_auto_generated": True}]
        result = merge_assembly_steps([], generated)
        assert result == generated

    def test_manual_step_takes_precedence(self):
        existing = [{"step": 1, "label": {"en": "Manual"}}]  # no _auto_generated
        generated = [{"step": 1, "label": {"en": "Auto"}, "_auto_generated": True}]
        result = merge_assembly_steps(existing, generated)
        assert result[0]["label"]["en"] == "Manual"

    def test_extra_manual_steps_appended(self):
        existing = [{"step": 5, "label": {"en": "Extra"}}]
        generated = [{"step": 1, "label": {"en": "Auto"}, "_auto_generated": True}]
        result = merge_assembly_steps(existing, generated)
        assert len(result) == 2
        assert result[-1]["step"] == 5
