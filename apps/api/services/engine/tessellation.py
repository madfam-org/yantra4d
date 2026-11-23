"""Named tessellation profiles for CadQuery and graph renders (owner rulings M1–M3, 2026-11-22).

Design: docs/architecture/tessellation-profiles-and-mesh-gate.md.

Two profiles, chosen by the render request:

* ``print`` — the default and the only profile a public API caller can get. Ruling M1
  keeps today's numbers under this name: CadQuery's own export defaults, 0.1 linear
  tolerance *relative* to edge size and 0.1 rad angular. The runner's print branch
  calls the exporter exactly as it did before profiles existed, with no tolerance
  arguments, so the bytes a person downloads do not change (tested byte for byte).
  The 0.02 mm absolute bound the proposal describes comes later, and only if the
  report-only mesh gate shows CadQuery parts over 0.05 mm.
* ``preview`` — 0.02 mm *absolute* linear, 0.35 rad angular (ruling M2). Only the
  models pipeline may ask for it (ruling M3): the API honours it only while
  ``ALLOW_PREVIEW_TESSELLATION`` is set AND ``AUTH_ENABLED`` is false, the state the
  prerender workflow runs its local API in. Every other caller gets a 403.

The profile is part of the render cache key and of the artifact name whenever it is
not ``print`` (``render_cache._make_key``, ``render_orchestrator.extract_render_payload``),
so a preview mesh can never be served as a print file. Print keys are left exactly as
they were, so introducing the profile invalidates nothing.

OpenSCAD and implicit renders are not tessellated by CadQuery: their resolution is
written in the cartridge, and a profile changes nothing about them.

This module is imported by ``cq_runner`` running as a standalone script (its own
directory on ``sys.path``), so it depends on nothing but the standard library. The
policy that reads the application's ``Config`` is a function that imports it lazily.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PRINT = "print"
PREVIEW = "preview"
DEFAULT_PROFILE = PRINT

#: The request field that names a profile.
REQUEST_FIELD = "tessellation"

#: Export formats ``preview`` is offered for. The models pipeline asks for STL and
#: turns it into the GLB it optimizes; a preview STEP is meaningless (STEP carries no
#: tessellation) and a preview 3MF or GLB would be a second, untested export path.
PREVIEW_EXPORT_FORMATS = frozenset({"stl"})


@dataclass(frozen=True)
class TessellationProfile:
    name: str
    #: Linear deflection: millimetres when ``relative`` is False, a fraction of each
    #: edge's size when True (CadQuery's ``exportStl(relative=...)``).
    linear: float
    #: Angular deflection in radians.
    angular: float
    relative: bool


PROFILES: dict[str, TessellationProfile] = {
    # CadQuery's export defaults (cadquery.occ_impl.exporters.export: tolerance=0.1,
    # angularTolerance=0.1; Shape.exportStl: relative=True). Recorded for reference
    # and for the report; the print branch does not pass them, it relies on them.
    PRINT: TessellationProfile(PRINT, linear=0.1, angular=0.1, relative=True),
    PREVIEW: TessellationProfile(PREVIEW, linear=0.02, angular=0.35, relative=False),
}


class TessellationRequestError(ValueError):
    """A ``tessellation`` value the caller may not use; carries the HTTP answer."""

    def __init__(self, message: str, status_code: int, error_code: str):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


def profile(name: str | None) -> TessellationProfile:
    """The profile called *name*; ``None`` means the default. Unknown names raise."""
    key = DEFAULT_PROFILE if name is None else name
    try:
        return PROFILES[key]
    except KeyError:
        raise ValueError(
            f"unknown tessellation profile {name!r} (known: {', '.join(sorted(PROFILES))})"
        ) from None


def preview_allowed() -> bool:
    """Whether this API process may render the ``preview`` profile (ruling M3).

    Same shape as ``tier_service.harness_tier_override``: opt-in, off by default, and
    ignored outright while ``AUTH_ENABLED`` is true, so the variable escaping into a
    real deployment cannot hand a public caller a preview mesh.
    """
    from config import Config

    if not getattr(Config, "ALLOW_PREVIEW_TESSELLATION", False):
        return False
    if Config.AUTH_ENABLED:
        logger.warning(
            "ALLOW_PREVIEW_TESSELLATION ignored: it is only honoured while AUTH_ENABLED is false"
        )
        return False
    return True


def requested_profile(data: dict, export_format: str) -> str:
    """The profile a render request asks for, or ``TessellationRequestError``.

    Absent or ``"print"`` is ``print``. ``"preview"`` needs ``preview_allowed()`` and an
    export format in ``PREVIEW_EXPORT_FORMATS``. Anything else is refused rather than
    quietly rendered as print, so a caller never believes it got what it asked for.
    """
    raw = data.get(REQUEST_FIELD) if isinstance(data, dict) else None
    if raw is None or raw == PRINT:
        return PRINT
    if not isinstance(raw, str) or raw not in PROFILES:
        raise TessellationRequestError(
            f"Unknown tessellation profile {raw!r}; the render API accepts only {PRINT!r}.",
            status_code=400,
            error_code="invalid_tessellation",
        )
    if not preview_allowed():
        raise TessellationRequestError(
            f"The {raw!r} tessellation profile is reserved for the models pipeline; "
            f"renders served by this API use {PRINT!r}.",
            status_code=403,
            error_code="tessellation_not_allowed",
        )
    if export_format not in PREVIEW_EXPORT_FORMATS:
        raise TessellationRequestError(
            f"The {raw!r} tessellation profile is only offered for "
            f"{', '.join(sorted(PREVIEW_EXPORT_FORMATS))} exports, not {export_format!r}.",
            status_code=400,
            error_code="invalid_tessellation",
        )
    return raw


def key_fields(name: str | None) -> dict:
    """The cache-key / artifact-name fields for a profile: empty for ``print``.

    Empty for the default on purpose: every print key and artifact URL stays exactly
    what it was before profiles existed, and any other profile is disjoint from it.
    """
    if name is None or name == PRINT:
        return {}
    return {REQUEST_FIELD: name}
