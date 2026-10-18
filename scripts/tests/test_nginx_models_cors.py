"""The landing's /models/ answers the Studio cross-origin, and nothing else does.

The Studio (app.yantra4d.com) shows the prerendered default mesh on project
open by reading https://yantra4d.com/models/manifest.json and the
<slug>.lod0/lod1.glb it lists. Those responses had no
Access-Control-Allow-Origin, so the browser refused them (C1, 2026-10-18).

These tests hold: both /models/ locations send ACAO from the
``$models_cors_origin`` map (never ``*``) with ``Vary: Origin``; they still
include the security-headers snippet (nginx drops inherited add_header in a
block that declares its own; test_nginx_security_headers.py holds the general
rule); meshes stay immutable; the map allows exactly the Studio and local dev
origins; no other location sends CORS. When an ``nginx`` binary is on PATH,
test_nginx_security_headers.py's ``nginx -t`` covers this config too.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CONF = REPO / "apps" / "landing" / "nginx.conf"
INCLUDE = "include /etc/nginx/snippets/security-headers.conf;"
ACAO = "add_header Access-Control-Allow-Origin $models_cors_origin always;"
VARY = 'add_header Vary "Origin" always;'


def _text() -> str:
    return "\n".join(line.split("#", 1)[0] for line in CONF.read_text().splitlines())


def _blocks(text: str, opener: str) -> list[tuple[str, str]]:
    found = []
    for match in re.finditer(opener + r"\s+([^{]+)\{", text):
        depth, i = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        found.append((match.group(1).strip(), text[match.end():i - 1]))
    return found


def _location(header: str) -> str:
    for found, body in _blocks(_text(), "location"):
        if found == header:
            return body
    raise AssertionError(f"landing nginx.conf has no `location {header}`")


MODELS_LOCATIONS = ["= /models/manifest.json", r"~* ^/models/[^/]+\.glb$"]


@pytest.mark.parametrize("header", MODELS_LOCATIONS)
def test_models_locations_send_cors_and_keep_the_security_headers(header):
    body = _location(header)
    assert ACAO in body
    assert VARY in body
    assert INCLUDE in body, f"location {header} drops the security headers"


def test_meshes_stay_immutable_and_typed():
    body = _location(r"~* ^/models/[^/]+\.glb$")
    assert 'add_header Cache-Control "public, immutable";' in body
    assert "expires 1y;" in body
    assert "default_type model/gltf-binary;" in body


def test_manifest_keeps_its_one_hour_ttl():
    assert "expires 1h;" in _location("= /models/manifest.json")


def test_models_glb_location_precedes_the_generic_glb_one():
    # The first matching regex location wins; the generic `\.glb$` one has no CORS.
    text = _text()
    assert text.index(r"location ~* ^/models/[^/]+\.glb$") < text.index(r"location ~* \.glb$")


def test_cors_origin_map_allows_only_the_studio_and_local_dev():
    maps = [body for header, body in _blocks(_text(), "map") if header == "$http_origin $models_cors_origin"]
    assert len(maps) == 1, "expected one `map $http_origin $models_cors_origin`"
    entries = [line.strip() for line in maps[0].splitlines() if line.strip()]
    assert entries == [
        'default "";',
        '"https://app.yantra4d.com" $http_origin;',
        r'"~^http://localhost(:[0-9]+)?$" $http_origin;',
        r'"~^http://127\.0\.0\.1(:[0-9]+)?$" $http_origin;',
    ]


@pytest.mark.parametrize("origin, allowed", [
    ("https://app.yantra4d.com", True),
    ("http://localhost:5173", True),
    ("http://localhost", True),
    ("http://127.0.0.1:4321", True),
    ("https://yantra4d.com", False),  # same origin: needs no CORS
    ("https://app.yantra4d.com.evil.example", False),
    ("http://localhost.evil.example", False),
    ("https://localhost:5173", False),
    ("null", False),
])
def test_map_regexes_match_exactly_the_intended_origins(origin, allowed):
    # nginx map: exact strings first, then `~` regexes in order (PCRE; Python's
    # re agrees for these patterns). Read from the config, not restated here.
    body = next(b for h, b in _blocks(_text(), "map") if h == "$http_origin $models_cors_origin")
    keys = re.findall(r'^\s*"([^"]+)"\s+\$http_origin;', body, re.MULTILINE)
    exact = {k for k in keys if not k.startswith("~")}
    patterns = [k[1:] for k in keys if k.startswith("~")]
    matched = origin in exact or any(re.search(p, origin) for p in patterns)
    assert matched is allowed


def test_no_other_location_sends_cors_and_nothing_sends_a_wildcard():
    text = _text()
    assert 'Access-Control-Allow-Origin "*"' not in text
    assert "Access-Control-Allow-Origin *" not in text
    for header, body in _blocks(text, "location"):
        if header not in MODELS_LOCATIONS:
            assert "Access-Control-Allow-Origin" not in body, f"location {header} sends CORS"


def test_studio_csp_lets_the_studio_fetch_the_landing_models():
    # GLTFLoader and the manifest fetch are `connect-src`; without the landing
    # origin there the browser blocks them before CORS is even consulted.
    snippet = (REPO / "apps" / "studio" / "nginx-security-headers.conf").read_text()
    csp = re.search(r'Content-Security-Policy "([^"]+)"', snippet).group(1)
    connect = next(d.split()[1:] for d in (p.strip() for p in csp.split(";")) if d.startswith("connect-src "))
    assert "https://yantra4d.com" in connect
    assert not any("*" in src for src in connect), "connect-src must name origins, not wildcards"

