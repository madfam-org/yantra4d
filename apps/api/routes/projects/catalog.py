"""
Catalog Blueprint — NopSCADlib component catalog API.

Endpoints:
  GET /api/catalog/nopscadlib
      Returns list of available categories.

  GET /api/catalog/nopscadlib/<category>
      Returns parsed component list for the given category.
      e.g. /api/catalog/nopscadlib/ball_bearings
"""

import logging

from flask import Blueprint, jsonify

from utils.route_helpers import error_response
from services.core.nopscadlib_catalog import get_catalog, list_categories

catalog_bp = Blueprint("catalog", __name__)
logger = logging.getLogger(__name__)


@catalog_bp.route("/api/catalog/nopscadlib", methods=["GET"])
def list_catalog_categories():
    """Return all available NopSCADlib catalog categories."""
    return jsonify({
        "categories": list_categories(),
    })


@catalog_bp.route("/api/catalog/nopscadlib/<category>", methods=["GET"])
def get_catalog_category(category: str):
    """
    Return parsed component list for the given NopSCADlib category.

    Response:
      {
        "category": "ball_bearings",
        "count": 17,
        "components": [
          {
            "id": "608",
            "label": "608 (8×22×7mm)",
            "category": "ball_bearings",
            "specs": { "bore_diameter": 8, "outer_diameter": 22, "width": 7, "color": "black" },
            "parameters": { "bore_diameter": 8 },
            "supplier_search": "ball bearing 608"
          },
          ...
        ]
      }
    """
    components = get_catalog(category)
    if components is None:
        return error_response(f"Unknown catalog category: '{category}'", 404)

    return jsonify({
        "category": category,
        "count": len(components),
        "components": components,
    })
