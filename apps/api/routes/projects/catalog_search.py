"""Faceted catalog search API — the scalable discovery data layer.

`GET /api/catalog/search` replaces "fetch the entire enriched project list and filter
client-side" with server-side search + faceting + pagination over a cached index. It
scales to thousands of projects because the index is built once (memoized behind a
directory-mtime signature) and every query is an in-process filter.

    GET /api/catalog/search
        ?q=<text>                 whitespace-split, AND semantics
        &domain=<value>           facet filters (exact match)
        &difficulty=<value>
        &engine=<value>
        &geometry_type=<value>    CDG "connects via"
        &standard=<value>         real-world interoperability ("compatible with X")
        &material=<value>         material-awareness capability ("adapts to material")
        &material_aware=1         only objects that declare any material awareness
        &tag=<value>
        &hyperobject_only=1
        &sort=name|recent|complexity
        &limit=<n>&offset=<n>

    GET /api/catalog/facets       just the global facet value→count maps (for nav chrome)
"""
import logging

from flask import Blueprint, jsonify, request

from services.core.catalog_index import (
    get_catalog,
    hidden_for_caller,
    search_catalog,
    visible_facets,
)

logger = logging.getLogger(__name__)

catalog_search_bp = Blueprint("catalog_search", __name__)

_MAX_LIMIT = 120


def _arg(name: str) -> str | None:
    v = request.args.get(name)
    return v.strip() if v and v.strip() else None


@catalog_search_bp.route("/api/catalog/search", methods=["GET"])
def catalog_search():
    """Server-side faceted search over the project catalog."""
    try:
        limit = min(max(int(request.args.get("limit", 60)), 1), _MAX_LIMIT)
    except (TypeError, ValueError):
        limit = 60
    try:
        offset = max(int(request.args.get("offset", 0)), 0)
    except (TypeError, ValueError):
        offset = 0

    sort = request.args.get("sort", "name")
    if sort not in ("name", "recent", "complexity"):
        sort = "name"

    # Private cartridges follow /api/projects: hidden unless this caller may view
    # them, and then the answer depends on the caller, so no shared cache.
    hidden, any_private = hidden_for_caller()
    result = search_catalog(
        q=request.args.get("q", ""),
        domain=_arg("domain"),
        difficulty=_arg("difficulty"),
        engine=_arg("engine"),
        geometry_type=_arg("geometry_type"),
        standard=_arg("standard"),
        material=_arg("material"),
        material_aware=request.args.get("material_aware") in ("1", "true"),
        tag=_arg("tag"),
        hyperobject_only=request.args.get("hyperobject_only") in ("1", "true"),
        sort=sort,
        limit=limit,
        offset=offset,
        hidden=hidden,
    )
    resp = jsonify(result)
    resp.headers["Cache-Control"] = _cache_control(any_private)
    return resp


def _cache_control(any_private: bool) -> str:
    """Brief edge cache for a caller-independent answer; none once privacy applies.

    The index self-invalidates on project changes, so 120 s is safe for a public
    catalog. With any private record the answer depends on who is asking, and a
    shared cache would hand one caller's view to the next (same rule as
    /api/projects).
    """
    return "private, no-store" if any_private else "public, max-age=120"


@catalog_search_bp.route("/api/catalog/facets", methods=["GET"])
def catalog_facets():
    """Global facet value→count maps + total count, for building navigation chrome."""
    cat = get_catalog()
    hidden, any_private = hidden_for_caller(cat)
    facets, count = visible_facets(cat, hidden)
    resp = jsonify({"facets": facets, "count": count})
    resp.headers["Cache-Control"] = _cache_control(any_private)
    return resp
