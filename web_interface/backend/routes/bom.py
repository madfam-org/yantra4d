"""
BOM Blueprint
Handles /api/projects/<slug>/bom endpoint for bill of materials export.
"""
import csv
import io
import json
import logging
import os
import re

from flask import Blueprint, request, jsonify, Response

from config import Config

bom_bp = Blueprint("bom", __name__)
logger = logging.getLogger(__name__)


def _safe_eval_formula(formula, params: dict):
    """Evaluate a simple arithmetic formula with parameter substitution.

    Only supports: +, -, *, /, (), integers, floats, and parameter names.
    No builtins, no imports — deliberately restrictive for safety.
    """
    if isinstance(formula, (int, float)):
        return formula

    expr = str(formula)
    # Substitute parameter names with their values
    for key, value in sorted(params.items(), key=lambda x: -len(x[0])):
        expr = expr.replace(key, str(value))

    # Validate: only allow digits, operators, parens, whitespace, dots
    if not re.match(r'^[\d\s\+\-\*\/\(\)\.]+$', expr):
        raise ValueError(f"Unsafe expression: {formula}")

    return eval(expr)  # noqa: S307 — validated safe subset above


def _load_manifest(slug: str):
    projects_dir = Config.PROJECTS_DIR
    manifest_path = os.path.join(projects_dir, slug, "project.json")
    if not os.path.isfile(manifest_path):
        return None
    with open(manifest_path, "r") as f:
        return json.load(f)


@bom_bp.route("/api/projects/<slug>/bom", methods=["GET"])
def get_bom(slug: str):
    """Return BOM as JSON or CSV based on Accept header / format query param."""
    manifest = _load_manifest(slug)
    if not manifest:
        return jsonify({"error": "Project not found"}), 404

    hardware = (manifest.get("bom") or {}).get("hardware")
    if not hardware:
        return jsonify({"error": "No BOM defined for this project"}), 404

    # Get parameter values from query string
    params = {}
    for p in manifest.get("parameters", []):
        val = request.args.get(p["id"])
        if val is not None:
            try:
                params[p["id"]] = float(val) if "." in val else int(val)
            except ValueError:
                params[p["id"]] = val
        else:
            params[p["id"]] = p.get("default", 0)

    rows = []
    for item in hardware:
        try:
            qty = _safe_eval_formula(item["quantity_formula"], params)
        except Exception:
            qty = item["quantity_formula"]

        label = item.get("label", item["id"])
        if isinstance(label, dict):
            label = label.get("en", label.get("es", item["id"]))

        rows.append({
            "id": item["id"],
            "label": label,
            "quantity": qty,
            "unit": item.get("unit", "pcs"),
            "supplier_url": item.get("supplier_url", ""),
        })

    fmt = request.args.get("format", "json")
    if fmt == "csv" or "text/csv" in (request.headers.get("Accept") or ""):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "label", "quantity", "unit", "supplier_url"])
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={slug}_bom.csv"},
        )

    return jsonify({"bom": rows})
