#!/usr/bin/env python3
"""Mint ceq hyperobject cards (and textures) for every cartridge in the commons.

The batch driver behind ``scripts/qa/ceq_coverage.py``. For each cartridge in
``docs/commons-catalog.json`` it builds a render payload from the catalog entry
(enriched by the cartridge's ``project.json`` when checked out), POSTs it to
ceq's deterministic render API, and records the resulting URL + hash in the
sidecar index ``docs/ceq-coverage.json``.

Dynamic by construction: the cartridge list, and therefore every count, comes
from the catalog on disk at run time. Nothing about the size of the commons is
baked in here.

## Credential — ADR-006 client_credentials, minted per run

ceq authenticates a Janua-issued JWT with the ``ceq:render`` scope and audience
``ceq-api``. This driver mints one itself from a confidential client, the same
edge pattern as fashion-cabinet → yantra4d (``fashion-cabinet/apps/api/
body_render.py``):

    JANUA_ISSUER=https://…            # Janua issuer base URL
    CEQ_COVERAGE_CLIENT_ID=…
    CEQ_COVERAGE_CLIENT_SECRET=…      # from Enclii/Vault, never committed
    CEQ_API_URL=https://api.ceq.lol   # optional; this is the default

Service tokens are ~1h-lived with no refresh, so the token is fetched on demand
and re-minted ~60s before expiry — a long backfill outlives a single token and
must not die halfway through it.

**Until that client is registered, this script runs in ``--dry-run`` and exits
0.** That is the default when the credentials are absent: it prints the plan and
a sample payload so the mapping can be reviewed before a single paid render.

## Resumability

ceq's render is content-addressed: ``sha256({template, version, data})``. This
driver recomputes that hash locally (``lib/ceq_coverage_core.payload_hash``,
byte-identical to ceq's ``render_hash``) and skips any slug already in the
sidecar with the same payload hash. So a re-run after an interruption costs
nothing, and a payload or template-version change re-renders exactly the
affected slugs.

The template version is read from ``GET /v1/render/templates`` rather than
guessed, so a version bump on ceq's side is picked up automatically.

Usage:
    # plan only — no credential needed
    python3 scripts/dev/ceq_backfill.py --dry-run
    python3 scripts/dev/ceq_backfill.py --dry-run --limit 3 --show-payload

    # real backfill, once the client exists
    python3 scripts/dev/ceq_backfill.py --kinds card --limit 50
    python3 scripts/dev/ceq_backfill.py --only aerator-cache --kinds card,texture
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from base64 import b64encode
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.ceq_coverage_core import (  # noqa: E402
    ASSET_KINDS,
    CATALOG_PATH,
    DEFAULT_TEMPLATES,
    SIDECAR_PATH,
    CoverageError,
    build_payload,
    catalog_entries,
    load_catalog,
    load_manifest,
    load_sidecar,
    needs_render,
    payload_hash,
    upsert_record,
    write_sidecar,
)

# Identify honestly: urllib's default User-Agent is on Cloudflare's banned
# signature list and trips Error 1010 at the auth edge (learned the hard way on
# the fashion-cabinet → yantra4d edge).
USER_AGENT = "yantra4d-ceq-backfill/1.0 (+https://yantra4d.com)"

DEFAULT_CEQ_URL = "https://api.ceq.lol"
JANUA_TOKEN_PATH = "/api/v1/oauth/token"
CEQ_AUDIENCE = "ceq-api"
CEQ_RENDER_SCOPE = "ceq:render"
TOKEN_TIMEOUT_SECONDS = 15.0
TOKEN_REFRESH_SKEW_SECONDS = 60.0
RENDER_TIMEOUT_SECONDS = float(os.environ.get("CEQ_RENDER_TIMEOUT_SECONDS", "60"))

#: Politeness ceiling. ceq renders are real work (Pillow plates, FLUX textures)
#: and this driver walks the entire commons in one go; 60/min is the documented
#: default, overridable with --rate.
DEFAULT_RATE_PER_MIN = 60


class BackfillError(RuntimeError):
    """A configured-but-failing call (token mint or render)."""


# ──────────────────────────────────────────────────────────────────────────────
# HTTP (stdlib only — this script runs from a bare CI/python3, no deps)
# ──────────────────────────────────────────────────────────────────────────────

def _request(url: str, *, data: bytes | None, headers: dict[str, str], timeout: float,
             method: str = "GET") -> dict:
    req = urllib.request.Request(url, data=data, method=method)
    for key, value in headers.items():
        req.add_header(key, value)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise BackfillError(f"HTTP {exc.code} from {url} {detail}".strip()) from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise BackfillError(f"could not reach {url}: {getattr(exc, 'reason', exc)}") from exc


class CeqClient:
    """Minimal ceq render client with a self-minting Janua service token."""

    def __init__(self, base_url: str, issuer: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip("/")
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None
        self._token_exp: float = 0.0

    # -- auth ---------------------------------------------------------------

    def _mint_token(self) -> tuple[str, float]:
        url = self.issuer + JANUA_TOKEN_PATH
        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "scope": CEQ_RENDER_SCOPE,
                "audience": CEQ_AUDIENCE,
            }
        ).encode("utf-8")
        basic = b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode("ascii")
        try:
            data = _request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {basic}",
                },
                timeout=TOKEN_TIMEOUT_SECONDS,
                method="POST",
            )
        except BackfillError as exc:
            raise BackfillError(
                f"{exc} — check CEQ_COVERAGE_CLIENT_ID/SECRET and that the client "
                f"allows scope {CEQ_RENDER_SCOPE} for audience {CEQ_AUDIENCE}"
            ) from exc
        token = data.get("access_token")
        if not token:
            raise BackfillError("Janua token response had no access_token")
        try:
            ttl = float(data.get("expires_in", 3600))
        except (TypeError, ValueError):
            ttl = 3600.0
        return token, time.time() + ttl

    def token(self) -> str:
        """A valid bearer token, re-minted shortly before expiry."""
        if self._token and self._token_exp - TOKEN_REFRESH_SKEW_SECONDS > time.time():
            return self._token
        self._token, self._token_exp = self._mint_token()
        return self._token

    def _auth_headers(self, *, json_body: bool = False) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.token()}"}
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    # -- api ----------------------------------------------------------------

    def template_versions(self) -> dict[str, str]:
        """``{template_name: version}`` from ``GET /v1/render/templates``."""
        rows = _request(
            self.base_url + "/v1/render/templates",
            data=None,
            headers=self._auth_headers(),
            timeout=TOKEN_TIMEOUT_SECONDS,
        )
        if not isinstance(rows, list):
            raise BackfillError("GET /v1/render/templates did not return a list")
        return {str(r.get("name")): str(r.get("version")) for r in rows if isinstance(r, dict)}

    def render_card(self, template: str, data: dict) -> dict:
        """POST /v1/render/card. Returns the RenderResponse envelope."""
        body = json.dumps({"template": template, "data": data}).encode("utf-8")
        return _request(
            self.base_url + "/v1/render/card",
            data=body,
            headers=self._auth_headers(json_body=True),
            timeout=RENDER_TIMEOUT_SECONDS,
            method="POST",
        )


# ──────────────────────────────────────────────────────────────────────────────
# Planning
# ──────────────────────────────────────────────────────────────────────────────

def build_plan(entries, sidecar, kinds, templates, versions, projects_dir=None) -> list[dict]:
    """One item per (slug, kind) that still needs a render.

    ``versions`` maps template name → version; in dry-run without a credential
    it is a placeholder so the printed hashes are clearly marked as provisional.
    """
    plan = []
    for entry in entries:
        slug = str(entry["slug"])
        manifest = load_manifest(slug, projects_dir)
        for kind in kinds:
            template = templates[kind]
            version = versions.get(template, "")
            data = build_payload(kind, entry, manifest)
            phash = payload_hash(template, data, version)
            if not needs_render(sidecar, slug, kind, phash):
                continue
            plan.append(
                {
                    "slug": slug,
                    "kind": kind,
                    "template": template,
                    "template_version": version,
                    "payload_hash": phash,
                    "data": data,
                }
            )
    return plan


class RateLimiter:
    """Simple spacing limiter — at most ``per_minute`` calls per minute."""

    def __init__(self, per_minute: int, sleep=time.sleep, clock=time.monotonic):
        self.interval = 60.0 / per_minute if per_minute > 0 else 0.0
        self._sleep = sleep
        self._clock = clock
        # None, not 0.0: a monotonic clock may legitimately read 0.0, and a
        # falsy sentinel would silently skip the first spacing interval.
        self._last: float | None = None

    def wait(self) -> None:
        if self.interval <= 0:
            return
        if self._last is not None:
            gap = self.interval - (self._clock() - self._last)
            if gap > 0:
                self._sleep(gap)
        self._last = self._clock()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_backfill(client: CeqClient, plan, sidecar, sidecar_path: Path, *,
                 rate: RateLimiter, checkpoint_every: int = 10) -> tuple[int, int]:
    """Execute the plan. Returns ``(rendered, failed)``.

    The sidecar is flushed every ``checkpoint_every`` successes so an
    interrupted long run keeps everything it already paid for — the next run
    resumes from the flushed state.
    """
    rendered = failed = 0
    for i, item in enumerate(plan, start=1):
        rate.wait()
        try:
            resp = client.render_card(item["template"], item["data"])
        except BackfillError as exc:
            failed += 1
            print(f"  FAIL {item['slug']} {item['kind']}: {exc}", file=sys.stderr)
            continue
        record = {
            "url": str(resp.get("url", "")),
            "hash": str(resp.get("hash", "")),
            "rendered_at": _now_iso(),
            "template": item["template"],
            "template_version": str(resp.get("template_version", item["template_version"])),
            "payload_hash": item["payload_hash"],
        }
        if resp.get("storage_uri"):
            record["storage_uri"] = str(resp["storage_uri"])
        if "cached" in resp:
            record["cached"] = bool(resp["cached"])
        upsert_record(sidecar, item["slug"], item["kind"], record)
        rendered += 1
        print(f"  ok   {item['slug']} {item['kind']} -> {record['url']}"
              + ("  (cached)" if record.get("cached") else ""))
        if rendered % checkpoint_every == 0:
            write_sidecar(sidecar, sidecar_path)
    write_sidecar(sidecar, sidecar_path)
    return rendered, failed


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def parse_kinds(raw: str) -> list[str]:
    kinds = [k.strip() for k in raw.split(",") if k.strip()]
    unknown = [k for k in kinds if k not in ASSET_KINDS]
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown asset kind(s) {', '.join(unknown)} (known: {', '.join(ASSET_KINDS)})"
        )
    return kinds or list(ASSET_KINDS)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    ap.add_argument("--sidecar", type=Path, default=SIDECAR_PATH)
    ap.add_argument("--kinds", type=parse_kinds, default=list(ASSET_KINDS),
                    help=f"comma-separated asset kinds (default: {','.join(ASSET_KINDS)})")
    ap.add_argument("--card-template", default=DEFAULT_TEMPLATES["card"])
    ap.add_argument("--texture-template", default=DEFAULT_TEMPLATES["texture"])
    ap.add_argument("--limit", type=int, default=None, help="render at most N assets")
    ap.add_argument("--only", action="append", default=None, metavar="SLUG",
                    help="restrict to this slug (repeatable)")
    ap.add_argument("--rate", type=int, default=DEFAULT_RATE_PER_MIN,
                    help=f"max renders per minute (default {DEFAULT_RATE_PER_MIN}, 0 = unlimited)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and exit 0 without calling ceq (default when "
                         "credentials are absent)")
    ap.add_argument("--show-payload", action="store_true",
                    help="in dry-run, print a full sample payload")
    ap.add_argument("--ceq-url", default=os.environ.get("CEQ_API_URL", DEFAULT_CEQ_URL))
    args = ap.parse_args(argv)

    if args.rate > DEFAULT_RATE_PER_MIN:
        print(
            f"ceq backfill: --rate {args.rate} exceeds the polite ceiling; "
            f"clamping to {DEFAULT_RATE_PER_MIN}/min",
            file=sys.stderr,
        )
        args.rate = DEFAULT_RATE_PER_MIN

    templates = {"card": args.card_template, "texture": args.texture_template}

    try:
        catalog = load_catalog(args.catalog)
        sidecar = load_sidecar(args.sidecar)
    except CoverageError as exc:
        print(f"ceq backfill: FAILED — {exc}", file=sys.stderr)
        return 1

    entries = catalog_entries(catalog)
    if args.only:
        wanted = set(args.only)
        entries = [e for e in entries if str(e["slug"]) in wanted]
        unknown = wanted - {str(e["slug"]) for e in entries}
        if unknown:
            print(f"ceq backfill: FAILED — slug(s) not in the catalog: "
                  f"{', '.join(sorted(unknown))}", file=sys.stderr)
            return 1

    issuer = os.environ.get("JANUA_ISSUER")
    client_id = os.environ.get("CEQ_COVERAGE_CLIENT_ID")
    client_secret = os.environ.get("CEQ_COVERAGE_CLIENT_SECRET")
    have_creds = bool(issuer and client_id and client_secret)
    dry_run = args.dry_run or not have_creds

    client = None
    versions: dict[str, str] = {}
    if not dry_run:
        client = CeqClient(args.ceq_url, issuer, client_id, client_secret)
        try:
            versions = client.template_versions()
        except BackfillError as exc:
            print(f"ceq backfill: FAILED — {exc}", file=sys.stderr)
            return 1
        unknown_templates = [t for t in (templates[k] for k in args.kinds) if t not in versions]
        if unknown_templates:
            print(
                f"ceq backfill: FAILED — ceq does not serve template(s) "
                f"{', '.join(sorted(set(unknown_templates)))}; available: "
                f"{', '.join(sorted(versions))}",
                file=sys.stderr,
            )
            return 1

    plan = build_plan(entries, sidecar, args.kinds, templates, versions)
    if args.limit is not None:
        plan = plan[: max(args.limit, 0)]

    if dry_run:
        reason = "--dry-run" if args.dry_run else "no credentials in env"
        by_kind = {k: sum(1 for p in plan if p["kind"] == k) for k in args.kinds}
        print(
            f"ceq backfill (dry run, {reason}): {len(plan)} render(s) planned across "
            f"{len(entries)} cartridge(s) — "
            + ", ".join(f"{n} {k}" for k, n in by_kind.items())
        )
        if not have_creds:
            print(
                "  no credential: set JANUA_ISSUER, CEQ_COVERAGE_CLIENT_ID and "
                "CEQ_COVERAGE_CLIENT_SECRET to run for real"
            )
        print(
            "  template versions unknown without a credential; the payload hashes "
            "below are provisional (GET /v1/render/templates supplies the real ones)"
            if not versions
            else f"  template versions: {json.dumps(versions, sort_keys=True)}"
        )
        for item in plan[:10]:
            print(f"  plan {item['slug']} {item['kind']} template={item['template']} "
                  f"payload_hash={item['payload_hash'][:12]}")
        if len(plan) > 10:
            print(f"  … and {len(plan) - 10} more")
        if args.show_payload and plan:
            print("\n  sample payload (POST /v1/render/card):")
            print(json.dumps(
                {"template": plan[0]["template"], "data": plan[0]["data"]},
                indent=2, sort_keys=True, ensure_ascii=False,
            ))
        return 0

    if not plan:
        print("ceq backfill: nothing to do — every requested asset is already in the sidecar")
        return 0

    print(f"ceq backfill: {len(plan)} render(s) at <= {args.rate or 'unlimited'}/min")
    rendered, failed = run_backfill(
        client, plan, sidecar, args.sidecar, rate=RateLimiter(args.rate)
    )
    print(f"ceq backfill: {rendered} rendered, {failed} failed — sidecar {args.sidecar}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
