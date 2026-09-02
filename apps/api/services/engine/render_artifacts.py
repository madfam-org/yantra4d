"""Finding a project's render artifacts in the store.

Three routes — wall-thickness analysis, the FEA stress overlay and the Cotiza
export — all wanted "the newest mesh this project rendered", and all three
answered it the same way: `glob.glob` over `Config.STATIC_DIR` and sort by
`os.path.getmtime`. That works exactly as long as artifacts are files in a
directory this process can see. Under `RENDER_ARTIFACT_STORE=s3` the glob
matches nothing, the routes report "no rendered mesh found", and the user is
told to render something they already rendered.

So the lookup is asked of the store instead, which knows where its artifacts
are on either backend. The tie-breaking is preserved deliberately: the old code
globbed extension by extension in preference order and then ran a *stable* sort
by mtime, so two artifacts written in the same second resolved to the preferred
extension. Callers still expect GLB before STL.
"""
from __future__ import annotations

import logging

from config import Config
from services.storage import ArtifactStore, get_artifact_store

logger = logging.getLogger(__name__)

#: Mesh formats a render may leave behind, in the order callers prefer them.
#: GLB first: renders auto-convert STL to GLB for web delivery, and the GLB is
#: the artifact the viewer actually loaded.
MESH_EXTENSIONS = (".glb", ".stl", ".3mf")


def render_key_prefix(slug: str) -> str:
    """The key prefix every render of *slug* carries.

    Artifacts are named ``<slug>_preview_<hash>_<part>.<ext>`` — the same name
    `services.core.project_access.artifact_slug_candidates` reads the slug back
    out of, which is what makes the private-project gate work on a key.
    """
    return f"{slug}_{Config.STL_PREFIX}"


def find_latest_render_key(
    slug: str,
    extensions: tuple[str, ...] = MESH_EXTENSIONS,
    *,
    store: ArtifactStore | None = None,
) -> str | None:
    """Key of the most recently stored render artifact for *slug*, or ``None``.

    Ties on the stored timestamp are broken by *extensions* order, matching the
    stable sort the filesystem version relied on. That matters more on an
    object store than it did on disk: S3 timestamps have second resolution, so
    the mesh and its GLB companion — written milliseconds apart — routinely
    carry the *same* `LastModified`.
    """
    store = store or get_artifact_store()
    prefix = render_key_prefix(slug)
    ranks = {ext.lower(): rank for rank, ext in enumerate(extensions)}

    best: tuple[float, int, str] | None = None
    for info in store.list(prefix):
        name = info.key.rsplit("/", 1)[-1]
        suffix = name[name.rfind("."):].lower() if "." in name else ""
        rank = ranks.get(suffix)
        if rank is None:
            continue
        candidate = (-info.modified_at, rank, info.key)
        if best is None or candidate < best:
            best = candidate

    return best[2] if best is not None else None


def discard_render_artifacts(
    parts: list[str],
    stl_prefix: str,
    export_format: str,
    *,
    store: ArtifactStore | None = None,
) -> int:
    """Remove the previous render of *parts*, returning how many went away.

    Replaces `utils.route_helpers.cleanup_old_stl_files`, which built a path
    under the static directory and called `os.remove`. That silently did
    nothing against an object store: the stale objects stayed, and the next
    render's URL could be answered by the previous render's bytes until the GC
    got to them a day later.
    """
    store = store or get_artifact_store()
    removed = 0
    for part in parts:
        if store.delete(f"{stl_prefix}{part}.{export_format}"):
            removed += 1
    return removed
