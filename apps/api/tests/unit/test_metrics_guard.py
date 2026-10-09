"""The Prometheus exposition is served to in-cluster scrapers only.

api.yantra4d.com reaches port 5000 through cloudflared, which forwards the
public Host and adds Cloudflare edge headers. The in-cluster Prometheus scrapes
the pod IP with no Cloudflare headers. Public requests must see 404 on /metrics
(and /metrics/); a scraper must keep getting exposition text.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app
from utils.metrics import is_internal_host

SCRAPER_BASE = "http://10.42.1.2:5000"
PUBLIC_BASE = "https://api.yantra4d.com"


@pytest.fixture
def client(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "STATIC_DIR", tmp_path / "static")
    (tmp_path / "static").mkdir()
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.mark.parametrize("path", ["/metrics", "/metrics/"])
def test_public_host_gets_404(client, path):
    resp = client.get(path, base_url=PUBLIC_BASE)

    assert resp.status_code == 404
    assert b"yantra4d_renders_total" not in resp.data


@pytest.mark.parametrize("header", ["cf-connecting-ip", "cf-ray", "cdn-loop"])
def test_cloudflare_edge_header_gets_404_even_with_internal_host(client, header):
    # A spoofed internal Host does not help once the request crossed the edge.
    resp = client.get("/metrics", base_url=SCRAPER_BASE, headers={header: "203.0.113.7"})

    assert resp.status_code == 404
    assert b"yantra4d_renders_total" not in resp.data


def test_scraper_gets_exposition_text(client):
    resp = client.get("/metrics", base_url=SCRAPER_BASE)

    assert resp.status_code == 200
    assert resp.mimetype == "text/plain"
    assert b"# TYPE yantra4d_renders_total counter" in resp.data
    assert b"# TYPE yantra4d_cache_hits_total counter" in resp.data


@pytest.mark.parametrize(
    "base_url",
    [
        "http://yantra4d-backend.yantra4d.svc",
        "http://yantra4d-backend.yantra4d.svc.cluster.local:80",
        "http://localhost:5000",
        "http://[::1]:5000",
    ],
)
def test_other_internal_hosts_get_exposition(client, base_url):
    resp = client.get("/metrics", base_url=base_url)

    assert resp.status_code == 200
    assert b"# TYPE yantra4d_renders_total counter" in resp.data


def test_guard_leaves_the_rest_of_the_public_api_alone(client):
    resp = client.get("/api/health/live", base_url=PUBLIC_BASE, headers={"cf-connecting-ip": "203.0.113.7"})

    assert resp.status_code == 200


@pytest.mark.parametrize(
    ("host", "internal"),
    [
        ("10.42.1.2:5000", True),
        ("10.42.1.2", True),
        ("[fd00::1]:5000", True),
        ("fd00::1", True),
        ("localhost", True),
        ("LOCALHOST:5000", True),
        ("yantra4d-backend", True),
        ("yantra4d-backend.yantra4d.svc", True),
        ("yantra4d-backend.yantra4d.svc.cluster.local:80", True),
        ("api.yantra4d.com", False),
        ("api.yantra4d.com:443", False),
        ("api.yantra4d.com.", False),
        ("evil.svc.example.com", False),
        ("", False),
    ],
)
def test_is_internal_host(host, internal):
    assert is_internal_host(host) is internal
