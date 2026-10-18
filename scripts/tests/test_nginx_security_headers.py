"""Every Studio / landing response carries the security headers.

nginx drops ALL inherited ``add_header`` directives in a block that declares
any of its own. The Studio's ``location /`` and ``/assets/`` set Cache-Control,
so ``app.yantra4d.com/`` served no CSP, X-Frame-Options or nosniff (A1 D-5,
2026-10-18) while robots.txt on the same host had them. The headers now live in
one snippet per app, included at server level and in every location that
declares an ``add_header``. These tests hold that rule, the header set (HSTS
included, without preload) and the Dockerfile that installs the snippet.

nginx itself is not required: the configs are parsed here. When an ``nginx``
binary is on PATH the snippet path is rewritten and ``nginx -t`` runs too.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SNIPPET_PATH = "/etc/nginx/snippets/security-headers.conf"
INCLUDE = f"include {SNIPPET_PATH};"
APPS = ["studio", "landing"]
REQUIRED = {
    "X-Content-Type-Options": '"nosniff"',
    "X-Frame-Options": '"SAMEORIGIN"',
    "Referrer-Policy": '"strict-origin-when-cross-origin"',
    "Strict-Transport-Security": '"max-age=31536000; includeSubDomains"',
    "Content-Security-Policy": None,
}


def _strip_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _locations(server_body: str) -> list[tuple[str, str]]:
    """(header, body) for every location block; these configs do not nest them."""
    found = []
    for match in re.finditer(r"location\s+([^{]+)\{", server_body):
        depth, i = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(server_body[i], 0)
            i += 1
        found.append((match.group(1).strip(), server_body[match.end():i - 1]))
    return found


def _server_level(server_body: str) -> str:
    out, depth = [], 0
    for ch in server_body:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def _server_body(app: str) -> str:
    text = _strip_comments((REPO / "apps" / app / "nginx.conf").read_text())
    start = text.index("server {") + len("server {")
    return text[start:text.rindex("}")]


@pytest.mark.parametrize("app", APPS)
def test_snippet_included_at_server_level(app):
    assert INCLUDE in _server_level(_server_body(app))


@pytest.mark.parametrize("app", APPS)
def test_every_location_with_add_header_includes_the_snippet(app):
    body = _server_body(app)
    checked = 0
    for header, block in _locations(body):
        if "add_header" in block:
            checked += 1
            assert INCLUDE in block, f"{app} location {header} drops the security headers"
    assert checked, "expected at least one location with its own add_header"


@pytest.mark.parametrize("app", APPS)
def test_security_headers_live_only_in_the_snippet(app):
    body = _server_body(app)
    for name in REQUIRED:
        assert name not in body, f"{app}/nginx.conf sets {name} outside the snippet"


@pytest.mark.parametrize("app", APPS)
def test_snippet_carries_every_header_with_always(app):
    snippet = _strip_comments((REPO / "apps" / app / "nginx-security-headers.conf").read_text())
    for name, value in REQUIRED.items():
        line = next((ln for ln in snippet.splitlines() if f"add_header {name} " in ln), None)
        assert line, f"{app} snippet lacks {name}"
        assert line.rstrip().endswith("always;"), f"{app} {name} must be sent on error responses too"
        if value:
            assert value in line
    assert "preload" not in snippet


def test_studio_csp_is_not_loosened():
    snippet = (REPO / "apps" / "studio" / "nginx-security-headers.conf").read_text()
    csp = re.search(r'Content-Security-Policy "([^"]+)"', snippet).group(1)
    assert "script-src 'self' 'wasm-unsafe-eval' blob:;" in csp
    assert "frame-ancestors 'self' https://yantra4d.com;" in csp
    assert "object-src 'none'" in csp
    assert "unsafe-eval'" not in csp.replace("'wasm-unsafe-eval'", "")
    assert "cloudflareinsights" not in csp


@pytest.mark.parametrize("app", APPS)
def test_dockerfile_installs_the_snippet_where_it_is_included(app):
    dockerfile = (REPO / "apps" / app / "Dockerfile").read_text()
    assert f"COPY apps/{app}/nginx-security-headers.conf {SNIPPET_PATH}" in dockerfile
    # Not under conf.d: nginx:alpine includes conf.d/*.conf at http level.
    assert "/conf.d/" not in SNIPPET_PATH


@pytest.mark.skipif(shutil.which("nginx") is None, reason="nginx not installed")
@pytest.mark.parametrize("app", APPS)
def test_nginx_accepts_the_config(app, tmp_path):
    snippet = tmp_path / "security-headers.conf"
    snippet.write_text((REPO / "apps" / app / "nginx-security-headers.conf").read_text())
    server = (REPO / "apps" / app / "nginx.conf").read_text().replace(SNIPPET_PATH, str(snippet))
    server = server.replace("proxy_pass http://yantra4d-backend", "proxy_pass http://127.0.0.1:9")
    conf = tmp_path / "nginx.conf"
    conf.write_text(
        f"pid {tmp_path}/nginx.pid; error_log {tmp_path}/error.log;\n"
        f"events {{}}\nhttp {{ access_log off; {server} }}\n"
    )
    proc = subprocess.run(["nginx", "-t", "-c", str(conf), "-p", str(tmp_path)],
                          capture_output=True, text=True, timeout=30, check=False)
    assert proc.returncode == 0, proc.stderr
