"""The self-hosted compose stack renders the whole Commons out of the box.

Owner ruling C8 (2026-11-22): "your configurators are yours" must hold for a
`docker compose up` install, which runs with auth off. Auth off alone gates the
render path as `guest`, which may not use the CadQuery or graph engines that
most Commons cartridges need, so the compose file sets HARNESS_TIER. This pins
that it still does, that its default names a tier with both engines, and that
the stack stays auth-off (the override is ignored once auth is on).
"""
import json
import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
COMPOSE = REPO / "docker-compose.yml"
TIERS = REPO / "apps" / "api" / "tiers.json"


def _backend_env() -> dict[str, str]:
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    env: dict[str, str] = {}
    for item in compose["services"]["backend"]["environment"]:
        key, _, value = item.partition("=")
        env[key] = value
    return env


def _default_of(value: str) -> str:
    """`${NAME:-default}` -> `default`; a plain value is returned as is."""
    match = re.fullmatch(r"\$\{[A-Z_]+:-([^}]*)\}", value)
    return match.group(1) if match else value


def test_compose_stack_is_auth_off():
    assert _backend_env()["AUTH_ENABLED"] == "false"


def test_compose_default_tier_renders_cadquery_and_graph():
    env = _backend_env()
    assert "HARNESS_TIER" in env, "the self-hosted stack would render as guest"
    tier = _default_of(env["HARNESS_TIER"]).strip().lower()
    tiers = json.loads(TIERS.read_text(encoding="utf-8"))
    assert tier in tiers, f"{tier!r} is not a tier in tiers.json"
    assert tiers[tier]["cadquery_engine"] is True
    assert tiers[tier]["graph_engine"] is True
