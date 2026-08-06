"""Compatibility graph API — the CDG interoperability moat, exposed.

Turns the derived compatibility graph (services/core/compatibility_graph.py) into three
endpoints that let the UI answer the maker's real question: "what does this part fit?"

    GET /api/catalog/graph
        The whole derived graph: nodes (with degree), edges (with the shared standard +
        geometry), and standard-family clusters. For an overview / relationship map.

    GET /api/catalog/<slug>/works-with
        Everything one object physically interfaces with, grouped with the reason
        ("shares Arca-Swiss 38mm dovetail"). Drives the "Works with" section on a project.

    GET /api/catalog/families
        The standard-family clusters (value → member slugs), for family-based browsing.
"""
import logging

from flask import Blueprint, jsonify

from services.core.compatibility_graph import get_graph, works_with

logger = logging.getLogger(__name__)

compatibility_bp = Blueprint("compatibility", __name__)


@compatibility_bp.route("/api/catalog/graph", methods=["GET"])
def catalog_graph():
    """The full derived compatibility graph (nodes + edges + family clusters)."""
    g = get_graph()
    resp = jsonify({
        "nodes": g["nodes"],
        "edges": g["edges"],
        "family_sizes": g["family_sizes"],
        "node_count": g["node_count"],
        "edge_count": g["edge_count"],
    })
    resp.headers["Cache-Control"] = "public, max-age=120"
    return resp


@compatibility_bp.route("/api/catalog/<slug>/works-with", methods=["GET"])
def catalog_works_with(slug: str):
    """Compatibility partners of one object, grouped with the shared-standard reason."""
    resp = jsonify(works_with(slug))
    resp.headers["Cache-Control"] = "public, max-age=120"
    return resp


@compatibility_bp.route("/api/catalog/families", methods=["GET"])
def catalog_families():
    """Standard-family clusters: family → member slugs, largest first."""
    g = get_graph()
    families = [
        {"family": fs["family"], "members": fs["members"],
         "slugs": g["families"][fs["family"]]}
        for fs in g["family_sizes"]
    ]
    resp = jsonify({"families": families, "count": len(families)})
    resp.headers["Cache-Control"] = "public, max-age=120"
    return resp
