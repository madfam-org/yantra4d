"""The Studio's /projects route loads directly, and its thumbnails 404 honestly.

The catalog route ``/projects`` shares its name with ``apps/studio/public/projects/``
(the catalog thumbnails). With ``try_files $uri $uri/ /index.html`` nginx matched
the directory: ``GET /projects`` answered ``301 Location: http://app.yantra4d.com/projects/``
and ``/projects/`` answered ``403 Forbidden`` (V1 visitor journey, 2026-10-18), so
the Studio's own «Proyectos» link worked only as client-side navigation. A
thumbnail the image does not ship came back as ``200 text/html`` (index.html),
which three.js then failed to decode.

These tests hold the routing rules; when an ``nginx`` binary is on PATH,
test_nginx_security_headers.py's ``nginx -t`` covers the config too.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONF = REPO / "apps" / "studio" / "nginx.conf"


def _text() -> str:
    return "\n".join(line.split("#", 1)[0] for line in CONF.read_text().splitlines())


def _locations() -> dict[str, str]:
    text, found = _text(), {}
    for match in re.finditer(r"location\s+([^{]+)\{", text):
        depth, i = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        found[match.group(1).strip()] = text[match.end():i - 1]
    return found


def _server_level() -> str:
    text = _text()
    body = text[text.index("server {") + len("server {"):text.rindex("}")]
    out, depth = [], 0
    for ch in body:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def test_the_thumbnail_directory_still_shadows_the_route_name():
    # The reason for the rules below; if the directory moves, they can go.
    assert (REPO / "apps" / "studio" / "public" / "projects").is_dir()


def test_spa_fallback_never_matches_a_directory():
    body = _locations()["/"]
    try_files = re.search(r"try_files\s+([^;]+);", body).group(1).split()
    assert "$uri/" not in try_files
    assert try_files == ["$uri", "/index.html"]


def test_trailing_slash_catalog_goes_back_to_the_route():
    body = _locations()["= /projects/"]
    assert re.search(r"return\s+301\s+/projects;", body)


def test_missing_thumbnails_are_a_real_404():
    thumbs = [h for h in _locations() if h.startswith("~") and "/projects/" in h]
    assert len(thumbs) == 1
    pattern = thumbs[0].split(None, 1)[1]
    assert re.search(pattern, "/projects/ab-drive.webp")
    assert re.search(pattern, "/projects/gridfinity.svg")
    # A project path that is not an image stays a SPA route.
    assert not re.search(pattern, "/projects/gridfinity")
    assert re.search(r"try_files\s+\$uri\s+=404;", _locations()[thumbs[0]])


def test_redirects_are_relative():
    # TLS ends before this nginx, so an absolute redirect says http://.
    assert re.search(r"absolute_redirect\s+off;", _server_level())
