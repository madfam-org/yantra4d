"""
NopSCADlib Catalog Parser — extracts component specs from NopSCADlib vitamin SCAD files.

Supported categories:
  - ball_bearings  (bore, OD, width, color)
  - motors         (NEMA size, shaft diameter, length)
  - screws         (diameter, pitch, length)

The parser uses regex to extract array-literal component definitions from the
NopSCADlib vitamins/*.scad files. No OpenSCAD execution required.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

# Path to NopSCADlib vitamins directory (relative to repo root)
_VITAMINS_DIR = Path(__file__).parents[3] / "libs" / "NopSCADlib" / "vitamins"


# ---------------------------------------------------------------------------
# Ball Bearings
# ---------------------------------------------------------------------------
# Format: BB624 = ["624", bore, OD, width, color, ...];
_BB_PATTERN = re.compile(
    r'^BB\w+\s*=\s*\["(\w+)",\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*"(\w+)"',
    re.MULTILINE,
)


def _parse_ball_bearings() -> list[dict]:
    path = _VITAMINS_DIR / "ball_bearings.scad"
    if not path.exists():
        logger.warning("NopSCADlib ball_bearings.scad not found at %s", path)
        return []

    text = path.read_text(encoding="utf-8", errors="replace")
    results = []
    for m in _BB_PATTERN.finditer(text):
        name, bore, od, width, color = m.groups()
        results.append({
            "id": name,
            "label": f"{name} ({bore}×{od}×{width}mm)",
            "category": "ball_bearings",
            "specs": {
                "bore_diameter": float(bore),
                "outer_diameter": float(od),
                "width": float(width),
                "color": color,
            },
            "parameters": {
                "bore_diameter": float(bore),
            },
            "supplier_search": f"ball bearing {name}",
        })
    return results


# ---------------------------------------------------------------------------
# NEMA Stepper Motors
# ---------------------------------------------------------------------------
# Format: NEMA17_47 = ["NEMA17_47", width, length, shaft_bore/2, shaft_len, ...]
# The string ID is at index 0, width at index 1, length at index 2
_NEMA_PATTERN = re.compile(
    r'^NEMA\w+\s*=\s*\["(NEMA(\d+)[^"]*)",\s*([\d.]+),\s*([\d.]+)',
    re.MULTILINE,
)


def _parse_stepper_motors() -> list[dict]:
    path = _VITAMINS_DIR / "stepper_motors.scad"
    if not path.exists():
        logger.warning("NopSCADlib stepper_motors.scad not found at %s", path)
        return []

    text = path.read_text(encoding="utf-8", errors="replace")
    results = []
    seen_ids = set()
    for m in _NEMA_PATTERN.finditer(text):
        full_id, nema_num, width, length = m.groups()
        if full_id in seen_ids:
            continue
        seen_ids.add(full_id)
        label = f"NEMA {nema_num} — {full_id} ({width}×{width}mm, {length}mm)"
        results.append({
            "id": full_id,
            "label": label,
            "category": "stepper_motors",
            "specs": {
                "nema_size": int(nema_num),
                "frame_width": float(width),
                "body_length": float(length),
            },
            "parameters": {
                "nema_size": int(nema_num),
            },
            "supplier_search": f"NEMA {nema_num} stepper motor {full_id}",
        })
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_CATEGORY_PARSERS = {
    "ball_bearings": _parse_ball_bearings,
    "stepper_motors": _parse_stepper_motors,
}


@lru_cache(maxsize=16)
def get_catalog(category: str) -> list[dict]:
    """
    Return parsed component list for the given NopSCADlib category.
    Results are cached in-process.

    Args:
        category: One of 'ball_bearings', 'stepper_motors'

    Returns:
        List of component dicts with id, label, category, specs, parameters.
    """
    parser = _CATEGORY_PARSERS.get(category)
    if not parser:
        return []
    try:
        return parser()
    except Exception:
        logger.exception("Failed to parse NopSCADlib category: %s", category)
        return []


def list_categories() -> list[str]:
    """Return all supported catalog categories."""
    return list(_CATEGORY_PARSERS.keys())
