"""The Studio image builds its crawl files from docs/commons-catalog.json.

app.yantra4d.com answered /sitemap.xml and /llms.txt with 404 and robots.txt
with only Cloudflare's content-signals text (V1 visitor journey, F10, 2026-10-18):
nginx declared exact locations for the three, but nothing shipped them. The
Vite `crawl-files` plugin now writes them at build time from the generated
public-cartridge list. These tests hold the packaging that plugin depends on:
the catalog has to reach the Docker build, and a commons bump (which
regenerates the catalog) has to rebuild the Studio, or the sitemap goes stale
silently.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_studio_dockerfile_copies_the_catalog_before_the_build():
    text = (REPO / "apps" / "studio" / "Dockerfile").read_text()
    copy = text.index("COPY docs/commons-catalog.json /app/docs/commons-catalog.json")
    assert copy < text.index("RUN npm run build")


def test_dockerignore_lets_the_catalog_into_the_context():
    lines = [line.strip() for line in (REPO / ".dockerignore").read_text().splitlines()]
    assert "docs/" in lines
    assert "!docs/commons-catalog.json" in lines
    assert lines.index("!docs/commons-catalog.json") > lines.index("docs/")


def test_a_catalog_change_rebuilds_the_studio():
    text = (REPO / ".github" / "workflows" / "deploy.yml").read_text()
    block = re.search(r"^\s+studio:\n((?:\s+(?:- '.*'|#.*)\n)+)", text, re.MULTILINE)
    assert block, "studio path filter not found"
    assert "- 'docs/commons-catalog.json'" in block.group(1)


def test_nginx_serves_the_three_files_and_never_the_spa():
    conf = (REPO / "apps" / "studio" / "nginx.conf").read_text()
    for name in ("robots.txt", "sitemap.xml", "llms.txt"):
        assert re.search(rf"location = /{re.escape(name)}\s*\{{\s*try_files \$uri =404;\s*\}}", conf), name
