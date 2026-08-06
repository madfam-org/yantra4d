"""
Cart Blueprint
Handles /api/projects/<slug>/bom/cart endpoint for BOM-to-cart pricing via ForgeSight.
"""
import json
import logging

from flask import Blueprint, Response, jsonify, request

from extensions import limiter
from middleware.auth import require_tier
from routes.projects.bom import _safe_eval_formula
from services.integrations.forgesight import forgesight_client
from utils.project_resolver import require_project
from utils.route_helpers import error_response
from utils.validators import require_valid_slug

cart_bp = Blueprint("cart", __name__)
logger = logging.getLogger(__name__)


@cart_bp.route("/api/projects/<slug>/bom/cart", methods=["POST"])
@require_valid_slug
@require_project()
@require_tier("pro")
@limiter.limit("30/hour")
def get_cart(slug: str, project_dir) -> Response | tuple[Response, int]:
    """Resolve BOM items against ForgeSight for live pricing.

    Request body (optional):
        { "parameter_overrides": { "width": 5, "depth": 3 } }

    Returns enriched BOM with unit_price, lead_time_days, available fields
    from ForgeSight, or null pricing fields with an error message if unavailable.
    """
    manifest_path = project_dir / "project.json"
    if not manifest_path.is_file():
        return error_response("Project manifest not found", 404)
    with open(manifest_path) as f:
        manifest = json.load(f)

    hardware = (manifest.get("bom") or {}).get("hardware")
    if not hardware:
        return error_response("No BOM defined for this project", 404)

    # Build parameter values: defaults + query overrides
    params = {}
    for p in manifest.get("parameters", []):
        params[p["id"]] = p.get("default", 0)

    # Apply overrides from request body
    body = request.get_json(silent=True) or {}
    overrides = body.get("parameter_overrides", {})
    for key, val in overrides.items():
        if key in params:
            params[key] = val

    # Evaluate BOM formulas and build quote request
    bom_items = []
    for item in hardware:
        try:
            qty = int(_safe_eval_formula(item["quantity_formula"], params))
        except Exception:
            qty = 1

        label = item.get("label", item["id"])
        if isinstance(label, dict):
            label = label.get("en", label.get("es", item["id"]))

        bom_items.append({
            "id": item["id"],
            "label": label,
            "quantity": qty,
            "unit": item.get("unit", "pcs"),
            "supplier_url": item.get("supplier_url", ""),
            "part_name": label,
            "material": item.get("material", ""),
            "specs": item.get("specs", {}),
        })

    # Query ForgeSight
    quote = forgesight_client.get_quote(bom_items)

    # Merge pricing into BOM items
    price_by_name = {qi.part_name: qi for qi in quote.items}
    fallback_reason = quote.fallback_reason or quote.error
    enriched = []
    for item in bom_items:
        qi = price_by_name.get(item["part_name"])
        enriched.append({
            "id": item["id"],
            "label": item["label"],
            "quantity": item["quantity"],
            "unit": item["unit"],
            "supplier_url": item["supplier_url"],
            "unit_price": qi.unit_price if qi else None,
            "lead_time_days": qi.lead_time_days if qi else None,
            "available": qi.available if qi else False,
            "source": qi.source if qi else quote.source,
            "market_verified": qi.market_verified if qi else False,
            "fallback_reason": qi.fallback_reason if qi else fallback_reason,
        })

    return jsonify({
        "items": enriched,
        "total_price": quote.total_price,
        "currency": quote.currency,
        "valid_until": quote.valid_until,
        "source": quote.source,
        "provenance": quote.provenance,
        "market_verified": quote.market_verified,
        "fallback_reason": fallback_reason,
        "sample_count": quote.sample_count,
        "error": quote.error,
    })
