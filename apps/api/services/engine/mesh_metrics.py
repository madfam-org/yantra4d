"""
One seam for "mesh in, numbers out": integrity, volume, surface area, bbox,
centroid and body count of a rendered mesh.

Two implementations sit behind it:

* ``TrimeshOracle`` — today's code paths, unchanged: ``mesh_integrity.assess``
  for the watertight/manifold verdict and trimesh's own ``volume`` /
  ``area`` / ``bounds`` for the quote metrics. This is the default.
* ``GeomCoreOracle`` — the shared C++ library geom-core
  (https://github.com/madfam-org/geom-core), whose ``assess_integrity`` is a
  port of ``mesh_integrity.assess``. Used only when its Python module
  (``geom_core_py``, from the ``geom-core`` wheel) is importable.

``MESH_ORACLE`` chooses: ``trimesh`` (default), ``geomcore`` or ``both``.
``both`` computes with both oracles, returns the trimesh numbers (the path
that is live today stays authoritative during a parity soak), logs one
structured ``mesh_oracle_parity`` record per metric and increments
``mesh_oracle_parity_mismatch_total{metric}`` whenever the two disagree.

Trimesh still loads every file: format conversion stays trimesh's job, and
geom-core only parses binary STL. The geom-core oracle therefore receives the
already-loaded mesh and is handed a binary STL of it.

Known, documented differences (the parity soak measures them, it does not hide
them): geom-core welds exactly coincident vertices on load, so for a mesh that
arrives as unwelded triangle soup it can report "watertight" with no merge
tolerance where ``mesh_integrity.assess`` reports the same verdict *after* a
tolerance merge; and two shells that touch without shared vertices (an
in-memory concatenation never welded) are two closed bodies to trimesh but a
non-manifold contact to geom-core. Every file the API reads goes through
``trimesh.load``, which welds first, so both agree on loaded files. Wall
thickness and overhang stay on the trimesh analyzers:
their HTTP contract returns per-vertex/per-face arrays, which geom-core does
not expose to Python.

See docs/guides/production-checklist.md, "Mesh oracle (geom-core)".
"""
from __future__ import annotations

import json
import logging
import math
import os
import tempfile
import weakref
from dataclasses import dataclass
from typing import Any, Protocol

import trimesh

from services.engine.mesh_integrity import MeshIntegrity
from services.engine.mesh_integrity import assess as _trimesh_assess

logger = logging.getLogger(__name__)

ORACLE_ENV = "MESH_ORACLE"
MODES = ("trimesh", "geomcore", "both")
DEFAULT_MODE = "trimesh"

#: Two floats agree when they are within this relative tolerance (or the
#: absolute floor, for values near zero). Both oracles sum in double
#: precision; only summation order differs.
REL_TOL = 1e-6
ABS_TOL = 1e-9

#: The integrity fields compared in ``both`` mode. ``notes`` and
#: ``merge_tolerance`` are evidence, not verdicts, and differ by design (see
#: the module docstring), so they are not counted as mismatches.
INTEGRITY_FIELDS = (
    "watertight", "boundary_edges", "nonmanifold_edges", "euler_number",
    "winding_consistent", "volume",
)


@dataclass(frozen=True)
class QuoteMetrics:
    """What the Cotiza quote export sends, in mm units."""
    volume_mm3: float
    surface_area_mm2: float
    bbox_mm: tuple[float, float, float]


class MeshOracle(Protocol):
    name: str

    def integrity(self, mesh: trimesh.Trimesh, scale_hint: float | None = None) -> MeshIntegrity: ...
    def volume_mm3(self, mesh: trimesh.Trimesh) -> float: ...
    def surface_area_mm2(self, mesh: trimesh.Trimesh) -> float: ...
    def bbox_mm(self, mesh: trimesh.Trimesh) -> tuple[float, float, float]: ...
    def centroid_mm(self, mesh: trimesh.Trimesh) -> tuple[float, float, float]: ...
    def body_count(self, mesh: trimesh.Trimesh) -> int: ...


class TrimeshOracle:
    """Today's behaviour, byte for byte: the code the API ran before the seam."""
    name = "trimesh"

    def integrity(self, mesh, scale_hint=None):
        return _trimesh_assess(mesh, scale_hint)

    def volume_mm3(self, mesh):
        # Quote volume: only a closed, consistently wound, positive solid has
        # one; anything else quotes 0 rather than a meaningless flux integral.
        return float(abs(mesh.volume)) if mesh.is_volume else 0.0

    def surface_area_mm2(self, mesh):
        return float(mesh.area)

    def bbox_mm(self, mesh):
        bounds = mesh.bounds  # (2, 3): min and max corners
        return (float(bounds[1][0] - bounds[0][0]),
                float(bounds[1][1] - bounds[0][1]),
                float(bounds[1][2] - bounds[0][2]))

    def centroid_mm(self, mesh):
        # Volumetric centre of mass, the quantity geom-core's getCentroid is.
        return tuple(float(c) for c in mesh.center_mass)

    def body_count(self, mesh):
        return int(len(mesh.split(only_watertight=False)))


def geom_core_module():
    """``geom_core_py`` when the geom-core wheel is installed, else None."""
    try:
        import geom_core_py
    except ImportError:
        return None
    return geom_core_py


class GeomCoreOracle:
    """geom-core's analyzer, fed a binary STL of the trimesh-loaded mesh."""
    name = "geomcore"

    def __init__(self, module=None):
        self._gc = module or geom_core_module()
        if self._gc is None:
            raise RuntimeError("geom-core is not installed (no geom_core_py module)")
        # One parse per mesh, not one per metric: (weakref to mesh, analyzer).
        self._last: tuple[weakref.ref, Any] | None = None

    def _analyzer(self, mesh):
        if self._last is not None and self._last[0]() is mesh:
            return self._last[1]
        analyzer = self._load(mesh)
        self._last = (weakref.ref(mesh), analyzer)
        return analyzer

    def _load(self, mesh):
        if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
            raise ValueError("geom-core needs a non-empty triangle mesh")
        analyzer = self._gc.Analyzer()
        fd, path = tempfile.mkstemp(suffix=".stl", prefix="mesh_oracle_")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(trimesh.exchange.stl.export_stl(mesh))
            if not analyzer.load_stl(path):
                raise ValueError("geom-core could not parse the exported STL")
        finally:
            os.unlink(path)
        return analyzer

    def integrity(self, mesh, scale_hint=None):
        # Same guard verdicts as mesh_integrity.assess, so both oracles answer
        # a non-mesh or an empty mesh identically instead of one raising.
        if not isinstance(mesh, trimesh.Trimesh):
            return MeshIntegrity(False, -1, None, False, 0.0,
                                 notes=[f"not a triangle mesh: {type(mesh).__name__}"])
        if len(mesh.faces) == 0:
            return MeshIntegrity(False, 0, None, False, 0.0, notes=["mesh has no faces"])
        r = self._analyzer(mesh).assess_integrity(scale_hint)
        return MeshIntegrity(
            watertight=bool(r.watertight),
            boundary_edges=int(r.boundary_edges),
            euler_number=None if r.euler_number is None else int(r.euler_number),
            winding_consistent=bool(r.winding_consistent),
            volume=float(r.volume),
            nonmanifold_edges=int(r.nonmanifold_edges),
            merge_tolerance=None if r.merge_tolerance is None else float(r.merge_tolerance),
            notes=list(r.notes),
        )

    def volume_mm3(self, mesh):
        # Same policy as the trimesh path (trimesh.is_volume: watertight,
        # consistently wound, positive signed volume), judged by geom-core.
        analyzer = self._analyzer(mesh)
        r = analyzer.assess_integrity(None)
        if not (r.watertight and r.winding_consistent and not r.inverted):
            return 0.0
        return float(analyzer.get_volume())

    def surface_area_mm2(self, mesh):
        return float(self._analyzer(mesh).get_surface_area())

    def bbox_mm(self, mesh):
        v = self._analyzer(mesh).get_bounding_box()
        return (float(v.x), float(v.y), float(v.z))

    def centroid_mm(self, mesh):
        v = self._analyzer(mesh).get_centroid()
        return (float(v.x), float(v.y), float(v.z))

    def body_count(self, mesh):
        return int(self._analyzer(mesh).get_body_count())


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

_warned: set[str] = set()


def _warn_once(key: str, message: str, *args) -> None:
    if key not in _warned:
        _warned.add(key)
        logger.error(message, *args)


def oracle_mode() -> str:
    """The configured mode. An unknown value is an error, logged, and means trimesh."""
    raw = (os.getenv(ORACLE_ENV) or DEFAULT_MODE).strip().lower()
    if raw not in MODES:
        _warn_once(f"mode:{raw}", "%s=%r is not one of %s; using %s",
                   ORACLE_ENV, raw, "|".join(MODES), DEFAULT_MODE)
        return DEFAULT_MODE
    return raw


def _geomcore_or_none() -> GeomCoreOracle | None:
    try:
        return GeomCoreOracle()
    except RuntimeError:
        _warn_once("geomcore-missing",
                   "%s=%s asks for geom-core, but the geom-core wheel is not installed "
                   "(no geom_core_py module); mesh metrics use trimesh. Build the image "
                   "with GEOM_CORE_WHEEL_URL — docs/guides/production-checklist.md",
                   ORACLE_ENV, oracle_mode())
        return None


# ---------------------------------------------------------------------------
# Parity
# ---------------------------------------------------------------------------

def _agree(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
        return a == b
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return len(a) == len(b) and all(_agree(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=REL_TOL, abs_tol=ABS_TOL)
    return a == b


def _delta(a: Any, b: Any) -> Any:
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
        return None
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)) and len(a) == len(b):
        return [_delta(x, y) for x, y in zip(a, b)]
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(b) - float(a)
    return None


def _count_mismatch(metric: str) -> None:
    from utils.metrics import MESH_ORACLE_PARITY_MISMATCH
    MESH_ORACLE_PARITY_MISMATCH.labels(metric=metric).inc()


def record_parity(slug: str | None, metric: str, trimesh_value: Any, geomcore_value: Any) -> bool:
    """Log one parity record; count it when the oracles disagree. Returns agreement."""
    agree = _agree(trimesh_value, geomcore_value)
    record = {
        "slug": slug,
        "mode": "both",
        "metric": metric,
        "trimesh": trimesh_value,
        "geomcore": geomcore_value,
        "delta": _delta(trimesh_value, geomcore_value),
        "match": agree,
    }
    # The JSON formatter keeps only the message, so the record IS the message.
    logger.log(logging.INFO if agree else logging.WARNING,
               "mesh_oracle_parity %s", json.dumps(record, sort_keys=True, default=str))
    if not agree:
        _count_mismatch(metric)
    return agree


def _compare(slug, metric, primary_fn, secondary_fn):
    """Run the primary oracle; in both mode also the secondary, and record parity.

    The secondary oracle never fails the caller: an exception there is itself
    a parity record (geomcore value = the error) and a mismatch.
    """
    value = primary_fn()
    try:
        other = secondary_fn()
    except Exception as exc:  # noqa: BLE001 — a failing secondary is data, not a crash
        other = f"error: {type(exc).__name__}: {exc}"
    record_parity(slug, metric, value, other)
    return value


def _oracles(primary: MeshOracle | None = None, secondary: MeshOracle | None = None):
    """(primary, secondary-or-None) for the configured mode."""
    mode = oracle_mode()
    if primary is not None:
        return primary, secondary
    if mode == "trimesh":
        return TrimeshOracle(), None
    gc = _geomcore_or_none()
    if gc is None:
        return TrimeshOracle(), None
    if mode == "geomcore":
        return gc, None
    return TrimeshOracle(), gc


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def quote_metrics(mesh, slug: str | None = None, *,
                  primary: MeshOracle | None = None,
                  secondary: MeshOracle | None = None) -> QuoteMetrics:
    """Volume, surface area and bbox for a quote, from the configured oracle(s).

    ``primary``/``secondary`` exist for tests (inject a fake oracle); callers
    leave them unset and get the ``MESH_ORACLE`` selection.
    """
    first, second = _oracles(primary, secondary)
    if second is None:
        return QuoteMetrics(first.volume_mm3(mesh), first.surface_area_mm2(mesh), first.bbox_mm(mesh))
    return QuoteMetrics(
        _compare(slug, "volume_mm3", lambda: first.volume_mm3(mesh), lambda: second.volume_mm3(mesh)),
        _compare(slug, "surface_area_mm2", lambda: first.surface_area_mm2(mesh),
                 lambda: second.surface_area_mm2(mesh)),
        _compare(slug, "bbox_mm", lambda: first.bbox_mm(mesh), lambda: second.bbox_mm(mesh)),
    )


def integrity(mesh, scale_hint: float | None = None, slug: str | None = None, *,
              primary: MeshOracle | None = None,
              secondary: MeshOracle | None = None) -> MeshIntegrity:
    """The watertight/manifold verdict from the configured oracle(s)."""
    first, second = _oracles(primary, secondary)
    verdict = first.integrity(mesh, scale_hint)
    if second is None:
        return verdict
    try:
        other = second.integrity(mesh, scale_hint)
    except Exception as exc:  # noqa: BLE001 — see _compare
        record_parity(slug, "integrity", verdict.summary, f"error: {type(exc).__name__}: {exc}")
        return verdict
    for field_name in INTEGRITY_FIELDS:
        record_parity(slug, f"integrity.{field_name}",
                      getattr(verdict, field_name), getattr(other, field_name))
    return verdict


def observe_render(path: str, slug: str | None = None, part: str | None = None) -> MeshIntegrity | None:
    """Assess a finished render when a geom-core mode is on; never fails the render.

    With the default ``MESH_ORACLE=trimesh`` this returns None without loading
    anything, so the render path does exactly the work it did before the seam.
    Under ``geomcore`` or ``both`` it logs the verdict (and, under ``both``,
    the parity records) — observation only; a render is never rejected here.
    """
    if oracle_mode() == "trimesh":
        return None
    label = f"{slug}/{part}" if part else slug
    try:
        mesh = trimesh.load(path, force="mesh")
        verdict = integrity(mesh, slug=label)
    except Exception as exc:  # noqa: BLE001 — observation must not break a render
        logger.warning("mesh_oracle render integrity for %s skipped: %s", label, exc)
        return None
    logger.info("mesh_oracle render integrity %s: %s", label, verdict.summary)
    return verdict
