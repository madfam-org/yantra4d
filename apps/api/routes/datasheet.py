"""
Datasheet Blueprint
Handles /api/projects/<slug>/datasheet endpoint for PDF generation.
Uses reportlab if available, falls back to HTML.
"""
import html
import io
import json
import logging
import os

from flask import Blueprint, request, Response

from config import Config
from services.route_helpers import error_response

datasheet_bp = Blueprint("datasheet", __name__)
logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def _load_manifest(slug: str):
    projects_dir = Config.PROJECTS_DIR
    manifest_path = os.path.join(projects_dir, slug, "project.json")
    if not os.path.isfile(manifest_path):
        return None
    with open(manifest_path, "r") as f:
        return json.load(f)


def _get_label(obj, key="label", lang="en"):
    val = obj.get(key, obj.get("id", ""))
    if isinstance(val, dict):
        return val.get(lang, val.get("en", ""))
    return val


def _generate_pdf(manifest: dict, params: dict, lang: str = "en") -> bytes:
    """Generate a PDF datasheet using reportlab."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    project = manifest.get("project", {})
    elements.append(Paragraph(f"{project.get('name', 'Project')} — Datasheet", styles["Title"]))
    elements.append(Spacer(1, 10))

    if project.get("description"):
        elements.append(Paragraph(project["description"], styles["Normal"]))
        elements.append(Spacer(1, 10))

    # Parameters table
    elements.append(Paragraph("Parameters", styles["Heading2"]))
    param_data = [["Parameter", "Value"]]
    for p in manifest.get("parameters", []):
        label = _get_label(p, "label", lang)
        value = params.get(p["id"], p.get("default", ""))
        param_data.append([label, str(value)])

    if len(param_data) > 1:
        t = Table(param_data, colWidths=[200, 200])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rl_colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))

    # BOM table
    hardware = (manifest.get("bom") or {}).get("hardware")
    if hardware:
        elements.append(Paragraph("Bill of Materials", styles["Heading2"]))
        bom_data = [["Item", "Quantity", "Unit"]]
        for item in hardware:
            label = _get_label(item, "label", lang)
            qty = item.get("quantity_formula", "")
            bom_data.append([label, str(qty), item.get("unit", "pcs")])

        t = Table(bom_data, colWidths=[200, 100, 100])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rl_colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))

    # Assembly steps
    steps = manifest.get("assembly_steps")
    if steps:
        elements.append(Paragraph("Assembly Instructions", styles["Heading2"]))
        for step in steps:
            label = _get_label(step, "label", lang)
            elements.append(Paragraph(f"Step {step['step']}: {label}", styles["Normal"]))
            if step.get("notes"):
                notes = _get_label(step, "notes", lang)
                elements.append(Paragraph(f"  Note: {notes}", styles["Italic"]))
        elements.append(Spacer(1, 10))

    doc.build(elements)
    return buf.getvalue()


def _generate_html(manifest: dict, params: dict, lang: str = "en") -> str:
    """Generate a simple HTML datasheet as fallback."""
    esc = html.escape
    project = manifest.get("project", {})
    name = esc(str(project.get("name", "")))
    out = f"<html><head><title>{name} Datasheet</title></head><body>"
    out += f"<h1>{name} — Datasheet</h1>"

    if project.get("description"):
        out += f"<p>{esc(str(project['description']))}</p>"

    out += "<h2>Parameters</h2><table border='1' cellpadding='4'><tr><th>Parameter</th><th>Value</th></tr>"
    for p in manifest.get("parameters", []):
        label = esc(str(_get_label(p, "label", lang)))
        value = esc(str(params.get(p["id"], p.get("default", ""))))
        out += f"<tr><td>{label}</td><td>{value}</td></tr>"
    out += "</table>"

    hardware = (manifest.get("bom") or {}).get("hardware")
    if hardware:
        out += "<h2>Bill of Materials</h2><table border='1' cellpadding='4'><tr><th>Item</th><th>Qty</th><th>Unit</th></tr>"
        for item in hardware:
            label = esc(str(_get_label(item, "label", lang)))
            qty = esc(str(item.get("quantity_formula", "")))
            unit = esc(str(item.get("unit", "pcs")))
            out += f"<tr><td>{label}</td><td>{qty}</td><td>{unit}</td></tr>"
        out += "</table>"

    out += "</body></html>"
    return out


@datasheet_bp.route("/api/projects/<slug>/datasheet", methods=["GET"])
def generate_datasheet(slug: str) -> Response | tuple[Response, int]:
    """Generate a project datasheet as PDF (if reportlab available) or HTML."""
    manifest = _load_manifest(slug)
    if not manifest:
        return error_response("Project not found", 404)

    lang = request.args.get("lang", "en")
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

    fmt = request.args.get("format", "pdf" if HAS_REPORTLAB else "html")

    if fmt == "pdf" and HAS_REPORTLAB:
        pdf_bytes = _generate_pdf(manifest, params, lang)
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={slug}_datasheet.pdf"},
        )

    html = _generate_html(manifest, params, lang)
    return Response(html, mimetype="text/html")
