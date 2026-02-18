"""
Assembly Generator — derives ordered assembly_steps from BOSL2 attach()/position()
call graphs extracted by scad_analyzer.

Given a manifest and per-file SCAD analysis, this service:
  1. Builds a part-to-part attachment graph from attach()/position() calls
  2. Topologically sorts the graph to produce an assembly order
  3. Maps BOSL2 anchor names to camera positions
  4. Returns a list of assembly_steps compatible with the manifest schema
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# BOSL2 anchor → approximate camera position mapping
# Positions are unit vectors scaled to 100 for a reasonable view distance.
# ---------------------------------------------------------------------------
_ANCHOR_TO_CAMERA: dict[str, list[float]] = {
    "TOP":    [30, -30, 80],
    "BOTTOM": [30, -30, -80],
    "FRONT":  [0, -100, 20],
    "BACK":   [0, 100, 20],
    "LEFT":   [-100, 0, 20],
    "RIGHT":  [100, 0, 20],
    "CENTER": [50, -50, 30],
    # Compound anchors
    "TOP+FRONT": [0, -60, 60],
    "TOP+BACK":  [0, 60, 60],
    "TOP+LEFT":  [-60, 0, 60],
    "TOP+RIGHT": [60, 0, 60],
}
_DEFAULT_CAMERA = [50, -50, 30]


def _camera_for_anchor(anchor: str) -> list[float]:
    """Return a camera position for a BOSL2 anchor string."""
    return _ANCHOR_TO_CAMERA.get(anchor.upper().strip(), _DEFAULT_CAMERA)


# ---------------------------------------------------------------------------
# Attachment graph builder
# ---------------------------------------------------------------------------

def _build_attachment_graph(analysis: dict) -> dict[str, list[dict]]:
    """
    Build {part_id: [{child, anchor, parent_anchor}]} from per-file attachment data.

    Each file in the analysis is treated as a 'part'. Attachments within a file
    describe how child geometry connects to the parent context.
    """
    graph: dict[str, list[dict]] = {}

    for filename, file_data in analysis.get("files", {}).items():
        part_id = filename.replace(".scad", "")
        graph.setdefault(part_id, [])

        for att in file_data.get("attachments", []):
            child = att.get("child", "")
            if child:
                graph[part_id].append({
                    "child": child,
                    "anchor": att.get("anchor", "TOP"),
                    "parent_anchor": att.get("parent_anchor", "TOP"),
                })

    return graph


def _topological_sort(graph: dict[str, list[dict]]) -> list[str]:
    """
    Kahn's algorithm topological sort.
    Returns parts in assembly order (dependencies first).
    """
    # Build in-degree map
    all_nodes: set[str] = set(graph.keys())
    for deps in graph.values():
        for d in deps:
            all_nodes.add(d["child"])

    in_degree: dict[str, int] = {n: 0 for n in all_nodes}
    for parent, children in graph.items():
        for dep in children:
            in_degree[dep["child"]] = in_degree.get(dep["child"], 0) + 1

    queue = sorted([n for n, deg in in_degree.items() if deg == 0])
    order: list[str] = []

    while queue:
        node = queue.pop(0)
        order.append(node)
        for dep in sorted(graph.get(node, []), key=lambda d: d["child"]):
            in_degree[dep["child"]] -= 1
            if in_degree[dep["child"]] == 0:
                queue.append(dep["child"])

    # Append any remaining nodes (handles cycles gracefully)
    for node in sorted(all_nodes):
        if node not in order:
            order.append(node)

    return order


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_assembly_steps(
    manifest: dict,
    scad_analysis: dict,
) -> list[dict[str, Any]]:
    """
    Generate assembly_steps from a project manifest and SCAD analysis.

    Args:
        manifest:      Parsed project.json dict.
        scad_analysis: Output of scad_analyzer.analyze_directory().

    Returns:
        List of assembly step dicts compatible with the manifest schema.
    """
    graph = _build_attachment_graph(scad_analysis)
    order = _topological_sort(graph)

    # Build a lookup: part_id → manifest part definition
    parts_by_id = {p["id"]: p for p in manifest.get("parts", [])}

    steps: list[dict[str, Any]] = []
    visible_so_far: list[str] = []

    for i, part_id in enumerate(order, start=1):
        # Only include parts that exist in the manifest
        if part_id not in parts_by_id and order:
            # Try to match by prefix (e.g. "yantra4d_spur_gear" → "main")
            continue

        part_def = parts_by_id.get(part_id, {})
        label_en = part_def.get("label", {}).get("en", part_id.replace("_", " ").title()) \
            if isinstance(part_def.get("label"), dict) else str(part_def.get("label", part_id))
        label_es = part_def.get("label", {}).get("es", label_en) \
            if isinstance(part_def.get("label"), dict) else label_en

        # Determine camera from attachment anchor
        attachments = graph.get(part_id, [])
        anchor = attachments[0]["anchor"] if attachments else "TOP"
        camera = _camera_for_anchor(anchor)

        visible_so_far.append(part_id)

        step: dict[str, Any] = {
            "step": i,
            "label": {
                "en": f"Add {label_en}",
                "es": f"Añadir {label_es}",
            },
            "notes": {
                "en": f"Attach {label_en} to the assembly.",
                "es": f"Fija {label_es} al ensamble.",
            },
            "visible_parts": list(visible_so_far),
            "highlight_parts": [part_id],
            "camera": camera,
            "camera_target": [0, 0, 0],
            "_auto_generated": True,
        }
        steps.append(step)

    return steps


def merge_assembly_steps(
    existing: list[dict],
    generated: list[dict],
) -> list[dict]:
    """
    Merge auto-generated steps with any manually authored ones.
    Manual steps (without _auto_generated) take precedence.
    """
    manual = {s["step"]: s for s in existing if not s.get("_auto_generated")}
    merged = []
    for step in generated:
        n = step["step"]
        merged.append(manual.get(n, step))
    # Append any manual steps beyond the generated range
    for n, s in sorted(manual.items()):
        if n > len(generated):
            merged.append(s)
    return merged
