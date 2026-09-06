#!/usr/bin/env python3
"""Cross-check apps/api/Dockerfile's render environment against the spec.

The render image and ``hyperobjects-spec`` each describe the environment a
cartridge renders in, and until now nothing kept the two honest. The spec is
what a cartridge author reads and what child repos reproduce; the Dockerfile is
what actually renders in production. A drift between them is silent by
construction: the image keeps working, child repos keep rendering against a
different OpenSCAD, and the first symptom is geometry that differs between a
contributor's machine and the platform — which is exactly the class of bug the
dual-engine parity lane exists to catch and cannot, because both sides of that
comparison run in the same image.

So this compares, against ``y4d_spec.render_environment``:

  - APT_PACKAGES against the Dockerfile's ``apt-get install`` list, as SETS.
    Order is meaningless in a package list and a diff on order would be noise;
    what matters is that neither side carries a package the other does not.
  - OPENSCAD_VERSION and OPENSCAD_SHA256 against the ``ARG`` lines, EXACTLY.
    A version is a version, and a hash that is nearly right is wrong: the
    Dockerfile pipes the ARG straight into ``sha256sum -c``, so a mismatch
    there is the difference between a verified download and a different binary.

INACTIVE UNTIL THE PIN CATCHES UP
---------------------------------
``y4d_spec.render_environment`` is being added by lane L-G31 and is not in the
pinned spec (v0.1.1) this repo installs. An ImportError is therefore NOT a
failure — it is the expected state today, and the check exits 0 saying so in
one line. Wiring it now rather than after the bump means the guard is already
in place when the pin moves, instead of being a follow-up someone has to
remember; the day the pin bumps, this check starts comparing on its own with
no further change. Any OTHER import error is still an error: a spec that is
present but broken must not read as a spec that is merely old.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCKERFILE = REPO / "apps" / "api" / "Dockerfile"

# `ARG OPENSCAD_VERSION=2026.02.01` / `ARG OPENSCAD_SHA256=dad3a8d1...`
ARG_RE = re.compile(r"^\s*ARG\s+([A-Z0-9_]+)\s*=\s*(\S+)\s*$", re.MULTILINE)


def parse_args_block(text: str) -> dict:
    """Every top-level ``ARG NAME=value`` in the Dockerfile."""
    return {name: value for name, value in ARG_RE.findall(text)}


def parse_apt_packages(text: str) -> set:
    """The package names in the Dockerfile's ``apt-get install`` invocation.

    Deliberately literal rather than a shell parser: it reads from the
    ``apt-get install`` token to the end of that shell command, and keeps the
    bare words. A shell parser would be more general and less reviewable, and
    this file's job is to be obviously right about one known command.

    Dropped along the way: flags (``-y``, ``--no-install-recommends``), the
    line continuations, and anything after the ``&&`` that ends the install —
    the Dockerfile chains `wget`/`sha256sum`/`ln` onto the same RUN, and those
    are not packages.
    """
    idx = text.find("apt-get install")
    if idx == -1:
        return set()
    rest = text[idx + len("apt-get install"):]

    packages = set()
    for raw in rest.split("\n"):
        line = raw.strip()
        # `\` continues the install; the first line without one ends it, and so
        # does an `&&` chaining the next command on.
        continues = line.endswith("\\")
        if continues:
            line = line[:-1].strip()
        for token in line.split():
            if token == "&&":
                return packages
            if token.startswith("-"):
                continue
            packages.add(token)
        if not continues:
            break
    return packages


def load_spec():
    """The spec's render environment, or None when the pin predates it.

    Returns (module, None) or (None, reason). Only a MISSING
    ``render_environment`` is a reason to stand down; anything else raises.
    """
    try:
        from y4d_spec import render_environment
    except ImportError as exc:
        name = getattr(exc, "name", "") or ""
        if name in ("y4d_spec", "y4d_spec.render_environment"):
            return None, str(exc)
        raise
    return render_environment, None


# Packages that exist only to BUILD an image (fetch the OpenSCAD AppImage,
# verify it) and never at render time. They are ignored on BOTH sides: the
# contract describes what a render environment needs, and whether an image
# fetches with wget or curl is its own business, never drift.
BUILD_ONLY_PACKAGES = frozenset({"wget", "curl", "ca-certificates"})


def compare(spec, dockerfile_text: str) -> list:
    """Every disagreement between the two, as human-readable lines."""
    problems = []

    spec_packages = set(spec.APT_PACKAGES) - BUILD_ONLY_PACKAGES
    image_packages = parse_apt_packages(dockerfile_text) - BUILD_ONLY_PACKAGES
    only_spec = sorted(spec_packages - image_packages)
    only_image = sorted(image_packages - spec_packages)
    if only_spec:
        problems.append(
            f"apt packages in the spec but not in apps/api/Dockerfile: "
            f"{', '.join(only_spec)}")
    if only_image:
        problems.append(
            f"apt packages in apps/api/Dockerfile but not in the spec: "
            f"{', '.join(only_image)}")

    args = parse_args_block(dockerfile_text)
    for arg, attr in (("OPENSCAD_VERSION", "OPENSCAD_VERSION"),
                      ("OPENSCAD_SHA256", "OPENSCAD_SHA256")):
        image_value = args.get(arg)
        spec_value = getattr(spec, attr)
        if image_value is None:
            problems.append(f"apps/api/Dockerfile declares no ARG {arg}")
        elif image_value != spec_value:
            problems.append(
                f"{arg} differs — spec {spec_value!r}, "
                f"apps/api/Dockerfile {image_value!r}")

    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Check apps/api/Dockerfile's render environment against "
                    "y4d_spec.render_environment.")
    ap.add_argument("--dockerfile", type=Path, default=DOCKERFILE,
                    help="Dockerfile to read (default: apps/api/Dockerfile)")
    args = ap.parse_args(argv)

    spec, inactive = load_spec()
    if spec is None:
        print(f"check_render_env: spec too old — check inactive "
              f"(no y4d_spec.render_environment: {inactive}). "
              f"It goes live with the next spec pin bump.")
        return 0

    if not args.dockerfile.is_file():
        print(f"check_render_env: FAIL — {args.dockerfile} not found")
        return 1

    problems = compare(spec, args.dockerfile.read_text(encoding="utf-8"))
    print(f"check_render_env: comparing {args.dockerfile} against "
          f"y4d_spec.render_environment — mismatches={len(problems)}")
    for p in problems:
        print(f"  FAIL {p}")
    if problems:
        print("  The render image and the spec must describe the same "
              "environment. Update whichever is wrong; if the image moved "
              "deliberately, bump the spec and re-pin it here.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
