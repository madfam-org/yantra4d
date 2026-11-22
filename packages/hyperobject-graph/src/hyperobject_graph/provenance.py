"""Licence and provenance: who may use a graph, and what it was made from.

Format 1.2 top-level fields::

    "licence": {"spdx": "CERN-OHL-W-2.0"},
    "provenance": {
      "authored": "generated",                     # "hand" or "generated"
      "generator": {"name": "...", "version": "..."},   # when generated
      "sources": [                                 # every file the graph runs or derives from
        {"path": "main.py", "sha256": "<64 hex>", "role": "script"}
      ]
    }

``role`` is ``"script"`` for a file a ``script`` node runs, ``"oracle"`` for a retired
script kept as a parity oracle (RFC 0067 G-5), ``"reference"`` for anything else a graph
was derived from. Every script node's source must be listed as a ``"script"`` source:
the digest is what makes an edit to the source without regenerating the wrapper a
visible drift rather than a silent one. The core checks the shape; the kernel that can
read the cartridge's files checks the digests (``source_digest_problems``).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable

from .errors import Problem, is_hashable_in
from .script_node import is_relative_source

#: An SPDX licence expression, shape only (ids, ``WITH``, ``AND``/``OR``, parentheses).
#: Which ids a commons accepts is the commons' rule, not the core's.
_SPDX_RE = re.compile(r"^[A-Za-z0-9.\-+() ]{1,128}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
AUTHORED = frozenset({"hand", "generated"})
SOURCE_ROLES = frozenset({"script", "oracle", "reference"})

__all__ = ["AUTHORED", "SOURCE_ROLES", "provenance_problems", "source_digest_problems"]


def provenance_problems(doc: dict, script_sources: set[str]) -> list[Problem]:
    problems: list[Problem] = []
    licence = doc.get("licence")
    if licence is not None:
        if not isinstance(licence, dict) or set(licence) - {"spdx", "notice"}:
            problems.append(Problem("licence", "/licence",
                                    "must be an object with 'spdx' and optionally 'notice'"))
        elif not isinstance(licence.get("spdx"), str) or not _SPDX_RE.match(licence["spdx"]):
            problems.append(Problem("licence", "/licence/spdx",
                                    "must be an SPDX licence expression"))

    prov = doc.get("provenance")
    listed: set[str] = set()
    if prov is not None:
        if not isinstance(prov, dict) or set(prov) - {"authored", "generator", "sources"}:
            problems.append(Problem(
                "provenance", "/provenance",
                "must be an object with 'authored', 'generator' and 'sources'",
            ))
            prov = {}
        if not is_hashable_in(prov.get("authored", "hand"), AUTHORED):
            problems.append(Problem("provenance", "/provenance/authored",
                                    f"must be one of {sorted(AUTHORED)}"))
        gen = prov.get("generator")
        if gen is not None and not (
            isinstance(gen, dict) and isinstance(gen.get("name"), str)
            and isinstance(gen.get("version"), str)
        ):
            problems.append(Problem("provenance", "/provenance/generator",
                                    "must be {'name': str, 'version': str}"))
        if prov.get("authored") == "generated" and gen is None:
            problems.append(Problem("provenance", "/provenance",
                                    "a generated graph names its generator"))
        sources = prov.get("sources", [])
        if not isinstance(sources, list):
            problems.append(Problem("provenance", "/provenance/sources", "must be an array"))
            sources = []
        for idx, src in enumerate(sources):
            loc = f"/provenance/sources/{idx}"
            if not isinstance(src, dict) or set(src) - {"path", "sha256", "role"}:
                problems.append(Problem("provenance", loc,
                                        "must be {'path', 'sha256', 'role'}"))
                continue
            if not is_relative_source(src.get("path")):
                problems.append(Problem("provenance", loc,
                                        "path must be relative and inside the cartridge"))
            if not isinstance(src.get("sha256"), str) or not _SHA256_RE.match(src["sha256"]):
                problems.append(Problem("provenance", loc, "sha256 must be 64 lowercase hex"))
            if not is_hashable_in(src.get("role"), SOURCE_ROLES):
                problems.append(Problem("provenance", loc,
                                        f"role must be one of {sorted(SOURCE_ROLES)}"))
            if src.get("role") == "script" and isinstance(src.get("path"), str):
                listed.add(src["path"])
    for source in sorted(script_sources - listed):
        problems.append(Problem(
            "provenance", "/provenance/sources",
            f"script source {source!r} is not listed with its sha256 (role 'script')",
        ))
    return problems


def source_digest_problems(doc: dict, read_bytes: Callable[[str], bytes | None]) -> list[Problem]:
    """Compare every listed source's sha256 with the file's bytes.

    ``read_bytes(path)`` returns the file's bytes or None when it does not exist; the
    caller resolves the path inside the cartridge (and refuses one that escapes it).
    """
    problems: list[Problem] = []
    prov = doc.get("provenance")
    if not isinstance(prov, dict):
        return problems
    for idx, src in enumerate(prov.get("sources") or []):
        if not isinstance(src, dict) or not isinstance(src.get("path"), str):
            continue
        data = read_bytes(src["path"])
        loc = f"/provenance/sources/{idx}"
        if data is None:
            problems.append(Problem("provenance", loc, f"{src['path']!r} does not exist"))
            continue
        actual = hashlib.sha256(data).hexdigest()
        if actual != src.get("sha256"):
            problems.append(Problem(
                "source-drift", loc,
                f"{src['path']!r} changed since the graph was made (sha256 {actual[:12]}…, "
                f"declared {str(src.get('sha256'))[:12]}…): regenerate the graph",
            ))
    return problems
