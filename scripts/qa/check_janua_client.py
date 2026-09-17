#!/usr/bin/env python3
"""Validate janua.client.yaml — the Studio's public Janua OIDC client — and read its pin.

WHY THIS EXISTS
---------------
The manifest is registered by the ecosystem provisioner
(`enclii secrets provision oidc --platform yantra4d-studio`), and several ways it
can be wrong are rejected only by Janua's server-side validator, after review and
merge. Each of these has happened in the ecosystem (telesia's check script records
the incidents); this repo inherits the guard:

  * THE WRONG REDIRECT. Janua matches `redirect_uri` BYTE FOR BYTE at the
    authorize and the token step, and the Studio's SDK sends its ORIGIN — no
    path, no trailing slash (VITE_JANUA_REDIRECT_URI in deploy.yml). A registered
    URI with a path the app never sends fails every login with
    `invalid_redirect_uri`, and because Janua also derives its CORS allow-list
    from active clients' redirect URIs, the browser could not even read the
    token response. This cross-checks the manifest against deploy.yml.
  * A CONFIDENTIAL FLAG ON A BROWSER CLIENT. The Studio holds no secret; PKCE is
    its proof. `is_confidential: true` here would make Janua demand a secret the
    Studio cannot present.
  * A THREE-SEGMENT SCOPE. Janua's grammar is `namespace:action`, exactly one
    colon; only standard OIDC scopes are exempt.
  * A PLAINTEXT REDIRECT on a non-loopback host hands the code to the network.
  * A MALFORMED PIN. `spec.client_id` must match ^jnc_[A-Za-z0-9_-]{8,56}$ or the
    re-run creates a duplicate instead of reconciling.

TWO MODES
---------
  check_janua_client.py                  CI: structure + cross-checks; an unpinned
                                         manifest is reported, not failed.
  check_janua_client.py --print-client-id
                                         deploy: prints EXACTLY one line,
                                         `client_id=jnc_…`, on stdout (everything
                                         else goes to stderr — stdout is appended
                                         to $GITHUB_OUTPUT, which rejects any other
                                         shape) and FAILS when unpinned — a Studio
                                         built without an id cannot sign anyone
                                         in, and Janua would only say so at the
                                         first click.

EXIT CODES
----------
  0  consistent (and, with --print-client-id, pinned)
  1  at least one finding
  2  inputs could not be established — NOT a pass
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

try:
    import yaml
except ImportError:  # pragma: no cover
    print("error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "janua.client.yaml"
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"

EXPECTED_API_VERSION = "janua.dev/v1"
EXPECTED_KIND = "OAuthClient"
EXPECTED_NAME = "yantra4d-studio"
# docs/AUTH.md → Audience: the `aud` the API validates (JANUA_AUDIENCE).
EXPECTED_AUDIENCE = "yantra4d-api"
SCOPE_RE = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$")
STANDARD_SCOPES = {"openid", "profile", "email", "offline_access", "address", "phone"}
CLIENT_ID_RE = re.compile(r"^jnc_[A-Za-z0-9_-]{8,56}$")
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}
# A browser client signs people in and refreshes; it never acts as itself.
ALLOWED_GRANTS = {"authorization_code", "refresh_token"}


def studio_redirect_uri_from_deploy(text: str) -> str | None:
    """VITE_JANUA_REDIRECT_URI from the Studio build's build-args in deploy.yml.

    Parsed as YAML rather than grepped: the admin build carries the same key
    with another origin, so a text search would be ambiguous.
    """
    try:
        wf = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    job = (wf.get("jobs") or {}).get("build-studio") or {}
    for step in job.get("steps") or []:
        args = ((step.get("with") or {}).get("build-args")) if isinstance(step, dict) else None
        if not isinstance(args, str):
            continue
        for line in args.splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key == "VITE_JANUA_REDIRECT_URI":
                return value.strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--print-client-id",
        action="store_true",
        help="print `client_id=<pin>` on stdout and fail when the manifest is not pinned",
    )
    args = parser.parse_args()

    # In --print-client-id mode stdout is machine-read (deploy.yml appends it to
    # $GITHUB_OUTPUT, whose parser rejected "client_id: pinned (…)" on the first
    # production deploy, 2026-09-17), so every human-facing line goes to stderr.
    info = sys.stderr if args.print_client_id else sys.stdout

    def say(message: str) -> None:
        print(message, file=info)

    if not MANIFEST.exists():
        print(f"UNKNOWN: {MANIFEST} is missing — the Studio's OIDC client declaration.", file=sys.stderr)
        return 2
    try:
        docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if isinstance(d, dict)]
    except yaml.YAMLError as exc:
        print(f"UNKNOWN: cannot parse {MANIFEST}: {exc}", file=sys.stderr)
        return 2
    if len(docs) != 1:
        print(
            f"UNKNOWN: expected exactly one document in {MANIFEST.name}, found {len(docs)}. "
            "Another client (the admin panel) belongs in its own manifest.",
            file=sys.stderr,
        )
        return 2

    doc = docs[0]
    meta = doc.get("metadata") or {}
    spec = doc.get("spec") or {}
    failures: list[str] = []

    # ── envelope ─────────────────────────────────────────────────────────────
    if doc.get("apiVersion") != EXPECTED_API_VERSION:
        failures.append(f"apiVersion is {doc.get('apiVersion')!r}, expected {EXPECTED_API_VERSION!r}.")
    if doc.get("kind") != EXPECTED_KIND:
        failures.append(f"kind is {doc.get('kind')!r}, expected {EXPECTED_KIND!r}.")
    if meta.get("name") != EXPECTED_NAME:
        failures.append(f"metadata.name is {meta.get('name')!r}, expected {EXPECTED_NAME!r}.")
    if spec.get("audience") != EXPECTED_AUDIENCE:
        failures.append(
            f"spec.audience is {spec.get('audience')!r}, expected {EXPECTED_AUDIENCE!r} — the `aud` "
            "apps/api validates (docs/AUTH.md → Audience)."
        )

    # ── pin ──────────────────────────────────────────────────────────────────
    client_id = spec.get("client_id")
    pinned = False
    if client_id is None:
        say("client_id: not pinned (expected only before first registration)")
    elif not isinstance(client_id, str) or not CLIENT_ID_RE.fullmatch(client_id):
        failures.append(
            f"spec.client_id is {client_id!r}, which does not match ^jnc_[A-Za-z0-9_-]{{8,56}}$. "
            "A malformed pin does not reconcile — it creates a duplicate."
        )
    else:
        pinned = True
        say(f"client_id: pinned ({client_id[:8]}…, {len(client_id)} chars)")

    # ── confidentiality ──────────────────────────────────────────────────────
    if spec.get("is_confidential") is not False:
        failures.append(
            f"spec.is_confidential is {spec.get('is_confidential')!r}, expected false. The Studio "
            "is a browser client: PKCE, no secret."
        )

    # ── redirect URIs ────────────────────────────────────────────────────────
    redirects = [str(u) for u in (spec.get("redirect_uris") or [])]
    for uri in redirects:
        parts = urlsplit(uri)
        host = parts.hostname or ""
        if parts.scheme == "http":
            if host not in LOOPBACK_HOSTS:
                failures.append(f"redirect_uri {uri!r} is plaintext http on a non-loopback host.")
        elif parts.scheme != "https":
            failures.append(f"redirect_uri {uri!r} has scheme {parts.scheme!r}.")
        if parts.path not in ("", "/") or parts.query or parts.fragment:
            failures.append(
                f"redirect_uri {uri!r} carries a path, query or fragment; the SDK sends the bare "
                "origin (VITE_JANUA_REDIRECT_URI), and Janua matches byte for byte."
            )
        if uri.endswith("/"):
            failures.append(f"redirect_uri {uri!r} ends with a slash; the SDK sends the origin without one.")

    deploy_origin = None
    if DEPLOY_WORKFLOW.exists():
        deploy_origin = studio_redirect_uri_from_deploy(DEPLOY_WORKFLOW.read_text())
    if deploy_origin is None:
        failures.append(
            "could not read VITE_JANUA_REDIRECT_URI from the build-studio job in "
            ".github/workflows/deploy.yml — the cross-check verified nothing."
        )
    elif deploy_origin not in redirects:
        failures.append(
            f"deploy.yml sends VITE_JANUA_REDIRECT_URI={deploy_origin!r} but the manifest does not "
            f"register it (registered: {redirects}). Every production login would fail with "
            "invalid_redirect_uri."
        )

    # ── scopes ───────────────────────────────────────────────────────────────
    scopes = [str(s) for s in (spec.get("allowed_scopes") or [])]
    for scope in scopes:
        if scope not in STANDARD_SCOPES and not SCOPE_RE.fullmatch(scope):
            failures.append(
                f"allowed_scope {scope!r} is not standard OIDC and does not match Janua's "
                "namespace:action grammar (exactly one colon)."
            )
    if "openid" not in scopes:
        failures.append("allowed_scopes lacks `openid`; there is no OIDC sign-in without it.")

    # ── grants ───────────────────────────────────────────────────────────────
    grants = [str(g) for g in (spec.get("grant_types") or [])]
    for grant in grants:
        if grant not in ALLOWED_GRANTS:
            failures.append(
                f"grant_type {grant!r} is not allowed for the Studio (allowed: {sorted(ALLOWED_GRANTS)})."
            )
    if "authorization_code" not in grants:
        failures.append("grant_types lacks `authorization_code`; the Studio signs people in with it.")

    # ── read proof ───────────────────────────────────────────────────────────
    say(f"checked: {len(redirects)} redirect URI(s), {len(scopes)} scope(s), {len(grants)} grant type(s)")
    if not redirects or not scopes or not grants:
        failures.append("a manifest declaring no redirect URI, no scope or no grant cannot log anybody in.")

    for line in failures:
        print(f"FAIL: {line}", file=sys.stderr)

    if args.print_client_id:
        if not pinned:
            print(
                "FAIL: spec.client_id is not pinned; a Studio built without its Janua client id cannot "
                "sign anyone in. Register the client (enclii secrets provision oidc --platform "
                "yantra4d-studio) and pin the returned jnc_… id here.",
                file=sys.stderr,
            )
            return 1
        if failures:
            return 1
        print(f"client_id={client_id}")
        return 0

    if failures:
        return 1
    say("OK: janua.client.yaml is consistent with deploy.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
