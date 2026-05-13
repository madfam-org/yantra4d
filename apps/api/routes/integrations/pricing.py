"""
Pricing Blueprint
Handles /api/pricing/benchmark endpoint for material price benchmarks.
Serves cached ForgeSight data or hardcoded fallback defaults.
"""
import logging

from flask import Blueprint, request, jsonify

from extensions import limiter
from services.integrations.forgesight import forgesight_client

pricing_bp = Blueprint("pricing", __name__)
logger = logging.getLogger(__name__)


@pricing_bp.route("/api/pricing/benchmark", methods=["GET"])
@limiter.limit("60/hour")
def get_benchmark():
    """Return material price benchmark (ForgeSight or fallback).

    Query params:
        material (str, required): Material ID (pla, petg, abs, tpu, resin, nylon)
        region (str, optional): Region code (default: CDMX)
        currency (str, optional): Preferred currency (MXN or USD, default: from source)
    """
    material = request.args.get("material", "").lower().strip()
    if not material:
        return jsonify({"error": "Missing required parameter: material"}), 400

    region = request.args.get("region")

    benchmark = forgesight_client.get_material_benchmark(material, region)

    return jsonify({
        "material": benchmark.material,
        "category": benchmark.category,
        "region": benchmark.region,
        "pricing": {
            "p10_per_kg": benchmark.p10_per_kg,
            "p50_per_kg": benchmark.p50_per_kg,
            "p90_per_kg": benchmark.p90_per_kg,
            "currency": benchmark.currency,
        },
        "source": benchmark.source,
        "provenance": benchmark.provenance,
        "market_verified": benchmark.market_verified,
        "fallback_reason": benchmark.fallback_reason,
        "sample_count": benchmark.sample_count,
        "updated_at": benchmark.updated_at,
        "error": benchmark.error,
    })


@pricing_bp.route("/api/pricing/materials", methods=["GET"])
@limiter.limit("60/hour")
def list_materials():
    """Return list of supported materials with ForgeSight category mappings."""
    return jsonify({
        "materials": forgesight_client.get_supported_materials(),
        "forgesight_available": forgesight_client.available,
    })
