#!/usr/bin/env python3
"""Validate every project manifest in projects/ against the manifest schema.

    python3 scripts/qa/validate_manifests.py
    python3 scripts/qa/validate_manifests.py --allow-uninitialised-submodules

Since RFC 0038 P2 the whole public commons is ONE submodule at `projects/`
(madfam-org/solid-hyperobjects), with each cartridge a directory at its root.
The read-proof this script exists for therefore moves up a level: instead of
asking "is each of the 37 registered projects/<slug> submodules checked out?",
it asks

    is the `projects` submodule initialised and non-empty?

An UNINITIALISED `projects` submodule is a FAILURE, not a skip. An empty
`projects/` only looks like a commons with no cartridges, and a checkout that
silently validates 0 cartridges instead of 500 is a checkout that proves
nothing. CI checks the submodule out explicitly, so on CI this failure means
the submodule fetch broke.

The client-private cartridges are NOT under `projects/` any more — they mount
at `private-projects/` and stay `update = none`, so they are never fetched by
`git submodule update` and this script never looks at them. That is why the
ratchet cannot fail on them: they are out of its scope by construction, not by
an exception.

Locally the commons is often left uninitialised on purpose. Pass
`--allow-uninitialised-submodules` (or set
`VALIDATE_MANIFESTS_ALLOW_UNINITIALISED=1`) to downgrade that failure to a
skip. Never set it in CI — it is the read-proof this script exists for.

A directory under `projects/` with no `project.json` is skipped as an ordinary
non-project directory, as before.

The run also fails when zero manifests were validated, so a bad path, an empty
checkout, or a future refactor that stops finding manifests cannot report
success by validating nothing.
"""
import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
PROJECTS_DIR = ROOT_DIR / "projects"
SCHEMA_PATH = ROOT_DIR / "packages" / "schemas" / "project-manifest.schema.json"
GITMODULES_PATH = ROOT_DIR / ".gitmodules"

#: The single submodule that carries the public commons. Its initialisation is
#: what this script ratchets on (RFC 0038 P2).
COMMONS_SUBMODULE_PATH = "projects"

# Cartridges whose manifests track an upstream project and are not ours to
# correct here. Validation issues for these are tracked upstream.
SKIP_VALIDATION = {
    "rubiks-hyperobject",  # upstream-tracked (preset/preview_hint schema drift)
}

# Classification results. VALID and the FAILED_* values are the only ones that
# move the exit code; the SKIPPED_* values differ only in what they report.
VALID = "valid"
SKIPPED_UPSTREAM = "skipped-upstream"
SKIPPED_PRIVATE = "skipped-private"
SKIPPED_UNINITIALISED = "skipped-uninitialised"
SKIPPED_NOT_A_PROJECT = "skipped-not-a-project"
FAILED_UNINITIALISED = "failed-uninitialised"
FAILED_INVALID = "failed-invalid"

SKIPPED_STATUSES = frozenset(
    {SKIPPED_UPSTREAM, SKIPPED_PRIVATE, SKIPPED_UNINITIALISED, SKIPPED_NOT_A_PROJECT}
)
FAILED_STATUSES = frozenset({FAILED_UNINITIALISED, FAILED_INVALID})

_SECTION_RE = re.compile(r'^\[submodule\s+"(?P<name>.*)"\]$')


def parse_gitmodules(path=GITMODULES_PATH):
    """Return {submodule path: {key: value}} from a .gitmodules file.

    Hand-rolled rather than configparser: `.gitmodules` indents its keys with a
    tab, which configparser reads as a continuation of the previous value.
    A missing .gitmodules yields {} — a repo with no submodules has nothing to
    classify, not an error.
    """
    submodules = {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(f"No .gitmodules at {path}; treating repo as submodule-free")
        return submodules

    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        section = _SECTION_RE.match(line)
        if section:
            current = {"name": section.group("name")}
            continue
        if current is None or "=" not in line:
            continue
        key, value = line.split("=", 1)
        current[key.strip().lower()] = value.strip()
        if "path" in current:
            submodules[current["path"]] = current
    return submodules


def commons_submodule_state(submodules, projects_dir=None):
    """Classify the `projects` submodule: (registered, initialised).

    `initialised` means the checkout actually has cartridges in it — a
    registered-but-unfetched submodule leaves an empty directory, and an empty
    directory is exactly what this must not accept as "a commons with nothing
    in it". Pure enough to unit-test: the .gitmodules half arrives parsed.
    """
    registered = COMMONS_SUBMODULE_PATH in submodules
    if projects_dir is None:
        projects_dir = PROJECTS_DIR
    try:
        initialised = any(
            child.is_dir() and (child / "project.json").exists()
            for child in Path(projects_dir).iterdir()
        )
    except (FileNotFoundError, NotADirectoryError):
        initialised = False
    return registered, initialised


def submodule_paths_under_projects(submodules):
    """Slugs of submodules registered directly under projects/.

    Empty since RFC 0038 P2 — the commons is one submodule AT `projects/`, not
    a submodule per cartridge under it. Kept because `classify_project` still
    takes the mapping, so a deployment that re-introduces per-cartridge
    gitlinks keeps its old behaviour rather than silently losing the check.
    """
    registered = {}
    for sub_path, config in submodules.items():
        parts = Path(sub_path).parts
        if len(parts) == 2 and parts[0] == "projects":
            registered[parts[1]] = config
    return registered


def load_schema(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Schema not found at {path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid schema JSON: {e}")
        return None


def classify_project(project_path, schema, registered_submodules, allow_uninitialised=False):
    """Classify one projects/<slug> directory.

    Returns (status, message). Pure enough to unit-test: everything it needs
    about submodule registration arrives in `registered_submodules`
    ({slug: {.gitmodules keys}}), so tests do not need a real git checkout.
    """
    project_slug = project_path.name
    manifest_path = project_path / "project.json"

    # Whether the submodule is CHECKED OUT is decided before whether its schema
    # is ours to police: SKIP_VALIDATION waives upstream schema drift, and must
    # not also waive "the fetch never happened".
    if not manifest_path.exists():
        submodule = registered_submodules.get(project_slug)
        if submodule is None:
            # Not a submodule and not a project — an ordinary directory.
            return SKIPPED_NOT_A_PROJECT, f"{project_slug} (no project.json, not a submodule — skipping)"
        if submodule.get("update") == "none":
            return SKIPPED_PRIVATE, (
                f"{project_slug} (skipped — submodule marked `update = none` in "
                f".gitmodules; client-private cartridge, never fetched)"
            )
        if allow_uninitialised:
            return SKIPPED_UNINITIALISED, (
                f"{project_slug} (skipped — submodule not initialised; allowed by "
                f"--allow-uninitialised-submodules)"
            )
        return FAILED_UNINITIALISED, (
            f"{project_slug}: submodule not initialised — projects/{project_slug} is "
            f"registered in .gitmodules but has no project.json, so its manifest was "
            f"never checked. Run `git submodule update --init projects/{project_slug}`, "
            f"or pass --allow-uninitialised-submodules for a local partial checkout."
        )

    if project_slug in SKIP_VALIDATION:
        return SKIPPED_UPSTREAM, f"{project_slug} (skipped — tracked upstream)"

    import jsonschema

    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        jsonschema.validate(instance=manifest, schema=schema)
        return VALID, f"{project_slug} valid"
    except json.JSONDecodeError as e:
        return FAILED_INVALID, f"{project_slug}: Invalid JSON in project.json - {e}"
    except jsonschema.ValidationError as e:
        return FAILED_INVALID, f"{project_slug}: Schema validation failed - {e.message}"
    except Exception as e:  # report, don't crash the whole sweep
        return FAILED_INVALID, f"{project_slug}: Unexpected error - {e}"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--allow-uninitialised-submodules",
        action="store_true",
        default=os.environ.get("VALIDATE_MANIFESTS_ALLOW_UNINITIALISED", "") not in ("", "0", "false", "False"),
        help=(
            "Treat a registered-but-uninitialised submodule under projects/ as a "
            "skip instead of a failure. For local partial checkouts only — CI "
            "checks out with `submodules: recursive` and must stay strict. Also "
            "settable via VALIDATE_MANIFESTS_ALLOW_UNINITIALISED=1."
        ),
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if not SCHEMA_PATH.exists():
        logger.error(f"Schema file missing: {SCHEMA_PATH}")
        return 1

    schema = load_schema(SCHEMA_PATH)
    if not schema:
        return 1

    # jsonschema is a hard dependency. Previously this ran
    # `os.system("pip install jsonschema")` — a script that mutates the
    # interpreter it is running under, silently, with an unchecked exit code.
    # CI's manifest-validation job already does `pip install jsonschema`.
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        logger.error(
            "jsonschema is required but not installed. Install it first:\n"
            "    pip install jsonschema\n"
            "(CI installs it in the manifest-validation job of .github/workflows/ci.yml.)"
        )
        return 1

    gitmodules = parse_gitmodules(GITMODULES_PATH)
    registered_submodules = submodule_paths_under_projects(gitmodules)

    # The #86 ratchet, re-targeted for RFC 0038 P2: the commons is one
    # submodule, so what must be proven is that IT came in.
    registered, initialised = commons_submodule_state(gitmodules)
    if registered and not initialised:
        if args.allow_uninitialised_submodules:
            logger.warning(
                f"⏭️  `{COMMONS_SUBMODULE_PATH}` submodule is not initialised — allowed "
                f"by --allow-uninitialised-submodules; NOTHING below was checked."
            )
        else:
            logger.error(
                f"`{COMMONS_SUBMODULE_PATH}` submodule is not initialised: it is registered "
                f"in .gitmodules but {PROJECTS_DIR} contains no cartridge, so no manifest "
                f"was checked. Run `git submodule update --init {COMMONS_SUBMODULE_PATH}`, "
                f"or pass --allow-uninitialised-submodules for a local partial checkout."
            )
            return 1

    project_dirs = [d for d in PROJECTS_DIR.iterdir() if d.is_dir()]
    project_dirs.sort()

    logger.info(f"Validating {len(project_dirs)} project directories against schema...")

    counts = {
        VALID: 0,
        SKIPPED_UPSTREAM: 0,
        SKIPPED_PRIVATE: 0,
        SKIPPED_UNINITIALISED: 0,
        SKIPPED_NOT_A_PROJECT: 0,
        FAILED_UNINITIALISED: 0,
        FAILED_INVALID: 0,
    }
    failures = []

    for project_dir in project_dirs:
        status, message = classify_project(
            project_dir, schema, registered_submodules, args.allow_uninitialised_submodules
        )
        counts[status] += 1
        if status == VALID:
            logger.info(f"✅ {message}")
        elif status in SKIPPED_STATUSES:
            logger.info(f"⏭️  {message}")
        else:
            logger.error(f"❌ {message}")
            failures.append(message)

    skipped_other = counts[SKIPPED_UPSTREAM] + counts[SKIPPED_NOT_A_PROJECT] + counts[SKIPPED_UNINITIALISED]
    failed = counts[FAILED_UNINITIALISED] + counts[FAILED_INVALID]

    logger.info("")
    logger.info(
        "Manifest validation summary: "
        f"{counts[VALID]} validated / "
        f"{counts[SKIPPED_PRIVATE]} skipped-private / "
        f"{skipped_other} skipped-other / "
        f"{failed} failed"
    )

    # Read-proof: a run that validated nothing has proven nothing, however
    # green it looks.
    if counts[VALID] == 0:
        logger.error(
            "No manifests were validated at all. Something is wrong with the "
            f"checkout or with PROJECTS_DIR ({PROJECTS_DIR})."
        )
        return 1

    if failed:
        logger.error(f"Validation failed for {failed} project directories.")
        return 1

    logger.info("All projects valid! ✨")
    return 0


if __name__ == "__main__":
    sys.exit(main())
