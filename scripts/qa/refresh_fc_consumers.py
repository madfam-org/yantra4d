#!/usr/bin/env python3
"""Vendor — and enforce — Fashion Cabinet's Yantra4D consumers back-edge.

Fashion Cabinet publishes `docs/interfaces/yantra4d-consumers.json` (contract
`yantra4d_consumers_v1`): per Yantra4D slug, the FC garments that consume that
solid and the Yantra4D parameter ids they drive. It is the back-edge of a bridge
whose front-edge already exists — FC vendors a pinned slice of this repo's
`docs/commons-catalog.json` and resolves its `hardware_ref` blocks against it.

Until now that pin ran one way: FC's CI knew when Yantra4D moved, and Yantra4D's
CI knew nothing about FC. So a parameter rename here — `foot_dia` -> `foot_d` on
a cartridge two garments drive — was green in this repo and red in theirs, days
later, in someone else's pull request. This script closes the loop:

    docs/interfaces/fashion-cabinet-consumers.snapshot.json

is a vendored, commit-pinned copy of FC's published file, and `--check` (a
blocking CI lane) resolves every linked claim in it against this repo's own
manifests. Rename a parameter a cabinet object depends on and *this* repo's CI
fails, naming the garment that breaks.

Mirrors FC's own `scripts/qa/refresh_hardware_snapshot.py` deliberately: a
vendored file rather than a submodule (which would import the other commons'
whole implementation) or a CI-time fetch (network in a fail-closed lane).
Neither repo reads the other's source; each pins a slice of the other's
published output, and refreshing that slice is a reviewable commit.

Usage:
    # vendor from a local fashion-cabinet checkout (records the pin you name)
    python3 scripts/qa/refresh_fc_consumers.py \
        --from-path ../fashion-cabinet/docs/interfaces/yantra4d-consumers.json \
        --pin-commit <fashion-cabinet sha>

    # vendor straight from a fashion-cabinet commit (network)
    python3 scripts/qa/refresh_fc_consumers.py --from-commit <sha>

    # CI lane: offline, deterministic, fail-closed
    python3 scripts/qa/refresh_fc_consumers.py --check

    # drift report against the pinned upstream commit (network; NOT in CI)
    python3 scripts/qa/refresh_fc_consumers.py --check-upstream

What `--check` enforces, for every *linked* consumer:

  1. the Yantra4D slug resolves in this repo — `projects/<slug>/project.json`,
     or `docs/commons-catalog.json` for a cartridge whose submodule is not
     checked out;
  2. every Yantra4D parameter that consumer drives is a real parameter of that
     cartridge;
  3. the vendored file is byte-identical to its own canonical re-serialisation,
     so a hand edit to the snapshot is caught rather than trusted.

Unlinked claims — FC's `wanted` list, and any consumer entry that carries an
explicit `linked: false` — are reported and never enforced. A co-create target
that has not been built here yet is an honest state, not a failure.

Parameter resolution prefers the on-disk manifest over the catalog. The catalog
is generated from those manifests, so trusting it first would let a rename pass
whenever the catalog had not been regenerated in the same commit — precisely the
drift this lane exists to catch. The catalog is the fallback for cartridges that
live in submodules, which are checked out in CI but often not locally.

No timestamps are written: the vendored file changes only when the upstream
content or the pin changes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROJECTS = REPO / "projects"
CATALOG = REPO / "docs" / "commons-catalog.json"
SNAPSHOT = REPO / "docs" / "interfaces" / "fashion-cabinet-consumers.snapshot.json"

SOURCE_REPO = "madfam-org/fashion-cabinet"
SOURCE_PATH = "docs/interfaces/yantra4d-consumers.json"
RAW_URL = "https://raw.githubusercontent.com/{repo}/{commit}/{path}"
API_URL = "https://api.github.com/repos/{repo}/contents/{path}?ref={commit}"
SUPPORTED_SCHEMA = "yantra4d_consumers_v1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

SNAPSHOT_COMMENT = (
    "VENDORED from Fashion Cabinet — do not hand-edit. A commit-pinned copy of "
    f"{SOURCE_REPO}:{SOURCE_PATH} (contract {SUPPORTED_SCHEMA}), the back-edge of the "
    "hardware bridge: which Fashion Cabinet garments consume which Yantra4D cartridge, "
    "and the parameter ids of ours they drive. Refresh with "
    "scripts/qa/refresh_fc_consumers.py; `--check` is a blocking CI lane that resolves "
    "every linked claim against this repo's manifests, so a parameter rename that would "
    "break a cabinet object fails here. See docs/reference/fashion-cabinet-consumers.md."
)


# ──────────────────────────────────────────────────────────────────────────────
# serialisation
# ──────────────────────────────────────────────────────────────────────────────

def canonical(doc: dict) -> str:
    """The one serialisation this file is ever written in.

    sort_keys makes the bytes a pure function of the content, so `--check` can
    prove the committed file is exactly what a re-vendor would produce.
    """
    return json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_snapshot(document: dict, commit: str) -> dict:
    """Wrap FC's published document in the pin that makes it citable."""
    return {
        "_comment": SNAPSHOT_COMMENT,
        "pin": {
            "source_repo": SOURCE_REPO,
            "source_path": SOURCE_PATH,
            "source_commit": commit,
            "source_schema_version": document.get("schema_version"),
        },
        "document": document,
    }


# ──────────────────────────────────────────────────────────────────────────────
# sources
# ──────────────────────────────────────────────────────────────────────────────

def _get_json(url: str, accept: str, token: str | None = None) -> dict:
    request = urllib.request.Request(url, headers={"Accept": accept})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 (fixed hosts)
        return json.loads(response.read().decode("utf-8"))


def fetch_upstream(commit: str) -> dict:
    """Read FC's published file at `commit`.

    raw.githubusercontent.com first: unauthenticated, and exactly the URL a
    human can paste into a browser to see what was vendored. It serves public
    repos only — and note it answers 404, not 401, both when the repo is private
    and when an Authorization header is attached at all, so none ever is.

    A commons can be private while it is being built, so when raw cannot serve
    the file and a token is in the environment (GITHUB_TOKEN / GH_TOKEN), the
    read is retried through the Contents API, which does authenticate. Tokens
    are read from the environment and never written anywhere.
    """
    raw_url = RAW_URL.format(repo=SOURCE_REPO, commit=commit, path=SOURCE_PATH)
    try:
        return _get_json(raw_url, accept="application/json")
    except (urllib.error.HTTPError, urllib.error.URLError):
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise
    api_url = API_URL.format(repo=SOURCE_REPO, commit=commit, path=SOURCE_PATH)
    return _get_json(api_url, accept="application/vnd.github.raw", token=token)


def source_problems(document: object) -> list[str]:
    """Shape checks on an FC document before it is vendored or trusted."""
    problems: list[str] = []
    if not isinstance(document, dict):
        return ["source document is not a JSON object"]

    schema = document.get("schema_version")
    if schema != SUPPORTED_SCHEMA:
        problems.append(
            f"source schema_version is {schema!r}, not {SUPPORTED_SCHEMA!r} — "
            "fashion-cabinet made a breaking change to the back-edge contract; "
            "update this script before re-vendoring"
        )
    consumers = document.get("consumers")
    if not isinstance(consumers, dict):
        return problems + ["source document has no 'consumers' object"]
    if not consumers:
        problems.append("source document lists no consumers — refusing an empty back-edge")

    for slug, entries in consumers.items():
        if not isinstance(entries, list):
            problems.append(f"consumers[{slug!r}] is not a list")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                problems.append(f"consumers[{slug!r}] holds a non-object entry")
                continue
            if not isinstance(entry.get("slug"), str):
                problems.append(f"consumers[{slug!r}] holds an entry with no 'slug'")
            drives = entry.get("drives")
            params_map = entry.get("params_map")
            if drives is not None and not isinstance(drives, list):
                problems.append(f"consumers[{slug!r}][{entry.get('slug')!r}].drives is not a list")
            if params_map is not None and not isinstance(params_map, dict):
                problems.append(
                    f"consumers[{slug!r}][{entry.get('slug')!r}].params_map is not an object"
                )
    return problems


def snapshot_problems(snapshot: object) -> list[str]:
    """Shape checks on the vendored file itself (pin block + payload)."""
    if not isinstance(snapshot, dict):
        return ["vendored snapshot is not a JSON object"]
    problems: list[str] = []
    pin = snapshot.get("pin")
    if not isinstance(pin, dict):
        problems.append("vendored snapshot has no 'pin' object")
    else:
        if pin.get("source_repo") != SOURCE_REPO:
            problems.append(
                f"pin.source_repo is {pin.get('source_repo')!r}, expected {SOURCE_REPO!r}"
            )
        if pin.get("source_path") != SOURCE_PATH:
            problems.append(
                f"pin.source_path is {pin.get('source_path')!r}, expected {SOURCE_PATH!r}"
            )
        commit = pin.get("source_commit")
        if not isinstance(commit, str) or not SHA_RE.match(commit):
            problems.append(
                f"pin.source_commit is {commit!r}, expected a full 40-character commit sha"
            )
    problems += source_problems(snapshot.get("document"))
    return problems


# ──────────────────────────────────────────────────────────────────────────────
# resolution against this repo
# ──────────────────────────────────────────────────────────────────────────────

def load_catalog() -> dict[str, dict]:
    if not CATALOG.exists():
        return {}
    catalog = _load_json(CATALOG)
    return {
        entry["slug"]: entry
        for entry in catalog.get("cartridges", [])
        if isinstance(entry, dict) and isinstance(entry.get("slug"), str)
    }


def _manifest_parameter_ids(slug: str) -> set[str] | None:
    """Parameter ids declared by projects/<slug>/project.json, or None if absent.

    Parameters are a top-level array in the manifest schema; per-mode scoping is
    expressed by a parameter's own `modes`/`visible_in_modes` list, not by a
    parameters block inside a mode. Every id a cartridge exposes is therefore in
    this one array, whichever mode shows it — which is what FC's params_map
    resolves against.
    """
    path = PROJECTS / slug / "project.json"
    if not path.exists():
        return None
    manifest = _load_json(path)
    return {
        parameter["id"]
        for parameter in (manifest.get("parameters") or [])
        if isinstance(parameter, dict) and isinstance(parameter.get("id"), str)
    }


def target_parameters(slug: str, catalog: dict[str, dict]) -> tuple[set[str] | None, str]:
    """(parameter ids, where they came from). None means the slug does not resolve."""
    ids = _manifest_parameter_ids(slug)
    if ids is not None:
        return ids, f"projects/{slug}/project.json"
    entry = catalog.get(slug)
    if entry is not None:
        return set(entry.get("parameter_ids") or []), "docs/commons-catalog.json"
    return None, ""


def consumer_claims(document: dict) -> list[tuple[str, dict, bool]]:
    """Flatten to (yantra4d slug, consumer entry, linked) in stable order.

    Everything under `consumers` is a link by contract (guarantee 2: unlinked
    claims live in `wanted`). An explicit `linked` field is honoured anyway —
    the contract is additive-only within v1, so a future FC release may start
    carrying one, and an unlinked claim must never fail this lane.
    """
    claims = []
    for slug in sorted(document.get("consumers") or {}):
        for entry in document["consumers"][slug]:
            claims.append((slug, entry, bool(entry.get("linked", True))))
    return claims


def driven_parameters(entry: dict) -> list[str]:
    """The Yantra4D parameter ids one consumer claims to drive.

    `drives` and the keys of `params_map` are both defined as parameter ids of
    the *target* cartridge. They agree today; the union is checked so that if
    they ever diverge, the lane reports it rather than silently trusting one.
    """
    ids = list(entry.get("drives") or [])
    ids += [key for key in (entry.get("params_map") or {}) if key not in ids]
    return ids


# ──────────────────────────────────────────────────────────────────────────────
# lanes
# ──────────────────────────────────────────────────────────────────────────────

def run_check(snapshot_path: Path) -> int:
    rel = snapshot_path.relative_to(REPO) if snapshot_path.is_relative_to(REPO) else snapshot_path
    print(f"fashion-cabinet consumers back-edge — {rel}")

    if not snapshot_path.exists():
        print(f"  FAIL vendored snapshot missing: {rel} — vendor it with "
              f"`python3 scripts/qa/refresh_fc_consumers.py --from-commit <sha>`")
        return 1

    raw = snapshot_path.read_text(encoding="utf-8")
    try:
        snapshot = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"  FAIL {rel} is not valid JSON: {exc}")
        return 1

    problems = snapshot_problems(snapshot)
    if problems:
        for problem in problems:
            print(f"  FAIL {problem}")
        return 1

    # Hand-edit tripwire. The vendored file is a pinned copy, not a working
    # document: if it is not byte-identical to its own canonical serialisation,
    # somebody edited it here instead of refreshing the pin.
    if raw != canonical(snapshot):
        print(f"  FAIL {rel} is not in canonical form — it was hand-edited, or written by "
              f"something other than this script. Re-vendor it "
              f"(`--from-path`/`--from-commit`) rather than editing it in place.")
        return 1

    pin = snapshot["pin"]
    document = snapshot["document"]
    resolved = (document.get("resolved_against") or {}).get("upstream_commit")
    print(f"  pinned at {pin['source_repo']}@{pin['source_commit'][:12]} ({pin['source_path']})")
    if resolved:
        print(f"  fashion-cabinet resolved these claims against yantra4d {resolved[:12]}")

    catalog = load_catalog()
    failures: list[str] = []
    informational: list[str] = []
    targets: set[str] = set()
    linked_consumers = 0
    checked_parameters = 0

    for slug, entry, linked in consumer_claims(document):
        fc_slug = entry.get("slug")
        parameters = driven_parameters(entry)
        if not linked:
            informational.append(
                f"unlinked consumer '{fc_slug}' claims yantra4d '{slug}' "
                f"({', '.join(parameters) or 'no parameters'}) — reported, not enforced"
            )
            continue

        targets.add(slug)
        linked_consumers += 1
        available, source = target_parameters(slug, catalog)
        if available is None:
            failures.append(
                f"fashion-cabinet consumer '{fc_slug}' is linked to yantra4d cartridge "
                f"'{slug}', which does not exist in this repo (no projects/{slug}/"
                f"project.json and no docs/commons-catalog.json entry)"
            )
            continue
        for parameter in parameters:
            checked_parameters += 1
            if parameter not in available:
                failures.append(
                    f"fashion-cabinet consumer '{fc_slug}' drives yantra4d '{slug}' "
                    f"parameter '{parameter}', which {source} does not declare "
                    f"(declared: {', '.join(sorted(available)) or 'none'})"
                )

    for claim in document.get("wanted") or []:
        target = claim.get("target_slug")
        available, _ = target_parameters(target, catalog) if isinstance(target, str) else (None, "")
        state = "built here" if available is not None else "not built here yet"
        requesting = ", ".join(claim.get("requesting") or []) or "nobody"
        informational.append(f"wanted '{target}' ({state}) — requested by {requesting}")

    print(f"  {len(targets)} yantra4d cartridges consumed, {linked_consumers} linked consumers, "
          f"{checked_parameters} parameter references checked")
    for note in informational:
        print(f"  note: {note}")

    if failures:
        for failure in failures:
            print(f"  FAIL {failure}")
        print(f"  {len(failures)} broken cross-commons claim(s). Either restore the parameter/"
              f"cartridge, or land the rename in fashion-cabinet first and re-vendor this "
              f"snapshot at the fashion-cabinet commit that carries it.")
        return 1

    print("  OK — every linked fashion-cabinet claim resolves against this repo")
    return 0


def run_vendor(document: dict, commit: str, snapshot_path: Path) -> int:
    problems = source_problems(document)
    if problems:
        for problem in problems:
            print(f"  FAIL {problem}")
        return 1
    if not SHA_RE.match(commit):
        print(f"  FAIL pin commit {commit!r} is not a full 40-character commit sha — "
              f"the pin has to name an immutable fashion-cabinet commit, not a branch")
        return 1

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(canonical(build_snapshot(document, commit)), encoding="utf-8")
    consumers = document.get("consumers") or {}
    rel = snapshot_path.relative_to(REPO) if snapshot_path.is_relative_to(REPO) else snapshot_path
    print(f"  wrote {rel} @ {SOURCE_REPO}@{commit[:12]} "
          f"({len(consumers)} cartridges, {sum(len(v) for v in consumers.values())} consumers)")
    return 0


def run_check_upstream(snapshot_path: Path, against: str | None) -> int:
    if not snapshot_path.exists():
        print(f"  FAIL vendored snapshot missing: {snapshot_path}")
        return 1
    snapshot = _load_json(snapshot_path)
    problems = snapshot_problems(snapshot)
    if problems:
        for problem in problems:
            print(f"  FAIL {problem}")
        return 1

    pinned = snapshot["pin"]["source_commit"]
    ref = against or pinned
    try:
        upstream = fetch_upstream(ref)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"  FAIL could not fetch {SOURCE_REPO}@{ref}:{SOURCE_PATH} — {exc}")
        return 1

    vendored = snapshot["document"]
    print(f"  comparing vendored copy against {SOURCE_REPO}@{ref}")
    if vendored == upstream:
        print("  OK — vendored copy is identical to upstream")
        return 0

    ours = vendored.get("consumers") or {}
    theirs = upstream.get("consumers") or {}
    added = sorted(set(theirs) - set(ours))
    removed = sorted(set(ours) - set(theirs))
    changed = sorted(s for s in set(ours) & set(theirs) if ours[s] != theirs[s])
    print(f"  DRIFT targets +{len(added)} -{len(removed)} ~{len(changed)}")
    for label, slugs in (("added", added), ("removed", removed), ("changed", changed)):
        if slugs:
            print(f"    {label}: {', '.join(slugs)}")
    if ref == pinned:
        # The pin names an immutable commit, so upstream cannot have moved:
        # a difference means the vendored copy was altered after vendoring.
        print("  FAIL the vendored copy differs from the commit it claims to pin — re-vendor it")
        return 1
    print(f"  (informational: refresh with `--from-commit <sha>` once {ref} is the pin you want)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                      help="CI lane: resolve every linked claim offline; fail closed")
    mode.add_argument("--check-upstream", action="store_true",
                      help="network: compare the vendored copy to its pinned upstream commit")
    mode.add_argument("--from-path", type=Path, metavar="FILE",
                      help="vendor from a local fashion-cabinet checkout (needs --pin-commit)")
    mode.add_argument("--from-commit", metavar="SHA",
                      help="vendor from a fashion-cabinet commit via raw.githubusercontent.com")
    parser.add_argument("--pin-commit", metavar="SHA",
                        help="the fashion-cabinet commit --from-path was taken from")
    parser.add_argument("--against", metavar="REF",
                        help="--check-upstream: compare against this ref instead of the pin")
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT, metavar="FILE",
                        help="vendored snapshot to read or write (default: the committed one)")
    args = parser.parse_args(argv)

    if args.check:
        return run_check(args.snapshot)
    if args.check_upstream:
        return run_check_upstream(args.snapshot, args.against)
    if args.from_path is not None:
        if not args.pin_commit:
            print("  FAIL --from-path needs --pin-commit <sha>: a vendored copy with no pin "
                  "cannot be verified against upstream later")
            return 1
        if not args.from_path.exists():
            print(f"  FAIL source file not found: {args.from_path}")
            return 1
        return run_vendor(_load_json(args.from_path), args.pin_commit, args.snapshot)

    commit = args.from_commit
    if args.pin_commit and args.pin_commit != commit:
        print(f"  FAIL --pin-commit {args.pin_commit!r} contradicts --from-commit {commit!r}")
        return 1
    try:
        document = fetch_upstream(commit)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"  FAIL could not fetch {SOURCE_REPO}@{commit}:{SOURCE_PATH} — {exc}")
        return 1
    return run_vendor(document, commit, args.snapshot)


if __name__ == "__main__":
    sys.exit(main())
