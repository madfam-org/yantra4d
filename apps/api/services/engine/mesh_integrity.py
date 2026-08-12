"""
Mesh integrity assessment for rendered geometry.

`trimesh.is_watertight` alone is not a safe verdict on an STL. STL stores each
triangle with its own copy of every vertex, so a perfectly closed solid arrives
as loose triangle soup and is only sealed once coincident vertices are merged.
Whether that merge succeeds depends on a floating-point tolerance, so a valid
mesh exported at one scale can read as "not watertight" purely from rounding.

Reporting that as a defect sends someone hunting a hole that does not exist;
ignoring it hides real ones. So assess in two steps — merge with a tolerance
appropriate to the model's own scale, then judge — and report *why* a mesh
failed rather than just that it did.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import trimesh


@dataclass
class MeshIntegrity:
    """Verdict plus the evidence behind it."""
    watertight: bool
    boundary_edges: int
    euler_number: int | None
    winding_consistent: bool
    volume: float
    merge_tolerance: float | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.watertight:
            tol = (f" after merging at {self.merge_tolerance:g}mm"
                   if self.merge_tolerance else "")
            return f"watertight{tol} (volume {self.volume:.2f})"
        return (f"NOT watertight — {self.boundary_edges} boundary edge(s), "
                f"euler {self.euler_number}, winding "
                f"{'consistent' if self.winding_consistent else 'INCONSISTENT'}")


def _count_boundary_edges(mesh: trimesh.Trimesh) -> int:
    """Edges used by exactly one face. A closed surface has none."""
    try:
        edges = np.sort(mesh.edges_sorted, axis=1)
        _, counts = np.unique(edges, axis=0, return_counts=True)
        return int((counts == 1).sum())
    except Exception:
        return -1


def assess(mesh: trimesh.Trimesh, scale_hint: float | None = None) -> MeshIntegrity:
    """Decide whether `mesh` encloses a volume, merging coincident vertices first.

    `scale_hint` is the characteristic size of the model in mm; the merge
    tolerance is derived from it so a 2mm part and a 200mm part are judged on
    the same relative precision rather than one absolute epsilon.
    """
    notes: list[str] = []

    if not isinstance(mesh, trimesh.Trimesh):
        return MeshIntegrity(False, -1, None, False, 0.0,
                             notes=[f"not a triangle mesh: {type(mesh).__name__}"])
    if len(mesh.faces) == 0:
        return MeshIntegrity(False, 0, None, False, 0.0, notes=["mesh has no faces"])

    if mesh.is_watertight:
        return MeshIntegrity(True, 0, int(mesh.euler_number),
                             bool(mesh.is_winding_consistent), float(mesh.volume))

    # Not sealed as loaded. Retry the merge at tolerances scaled to the model,
    # coarsest last, and stop at the first that closes it.
    extent = scale_hint or float(np.max(mesh.extents) if len(mesh.extents) else 1.0)
    for rel in (1e-8, 1e-7, 1e-6, 1e-5):
        tol = max(extent * rel, 1e-9)
        candidate = mesh.copy()
        # float() first: np.log10 yields a numpy scalar, whose round() returns a
        # numpy float rather than an int, and merge_vertices wants a digit count.
        digits = max(0, round(float(-np.log10(tol))))
        try:
            candidate.merge_vertices(digits_vertex=digits)
        except TypeError:
            # Older trimesh signatures take no tolerance argument.
            candidate.merge_vertices()
        if candidate.is_watertight:
            notes.append(f"sealed after merging coincident vertices at {tol:g}mm "
                         f"({len(mesh.vertices) - len(candidate.vertices)} merged) — "
                         f"STL float precision, not a hole in the model")
            return MeshIntegrity(True, 0, int(candidate.euler_number),
                                 bool(candidate.is_winding_consistent),
                                 float(candidate.volume), merge_tolerance=tol,
                                 notes=notes)

    # Genuinely open.
    boundary = _count_boundary_edges(mesh)
    if boundary > 0:
        notes.append(f"{boundary} edge(s) belong to only one face, so the surface "
                     f"does not close")
    if not mesh.is_winding_consistent:
        notes.append("face winding is inconsistent, which can invert normals and "
                     "break slicing even where the surface closes")
    return MeshIntegrity(False, boundary, int(mesh.euler_number),
                         bool(mesh.is_winding_consistent),
                         float(mesh.volume), notes=notes)
