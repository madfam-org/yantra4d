#!/usr/bin/env python3
"""Validate the OpenAPI spec, including duplicate keys the validator misses.

`openapi_spec_validator` parses with PyYAML, which resolves duplicate mapping
keys by silently keeping the last one. So a spec can define `/api/foo` twice —
with different tags, summaries and response schemas — and still validate
cleanly while half of it is discarded. That is exactly what happened to
`/api/catalog/nopscadlib`: two definitions, the earlier one dropped, and the
validation job green throughout.

This runs the duplicate-key check first, then the spec validator.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "docs" / "reference" / "openapi.yaml"


class DuplicateKeyError(ValueError):
    """A mapping defines the same key more than once."""


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys instead of overriding."""


def _no_duplicates(loader: yaml.Loader, node: yaml.MappingNode, deep: bool = False) -> dict:
    seen: set = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            mark = key_node.start_mark
            raise DuplicateKeyError(
                f"duplicate key {key!r} at line {mark.line + 1}, column {mark.column + 1} "
                f"— PyYAML would silently keep the last definition and discard the first"
            )
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates
)


def main() -> int:
    if not SPEC_PATH.is_file():
        print(f"MISSING: {SPEC_PATH.relative_to(REPO_ROOT)}")
        return 1

    text = SPEC_PATH.read_text(encoding="utf-8")

    try:
        yaml.load(text, Loader=_StrictLoader)
    except DuplicateKeyError as exc:
        print(f"ERROR: {SPEC_PATH.relative_to(REPO_ROOT)}: {exc}")
        return 1
    except yaml.YAMLError as exc:
        print(f"ERROR: {SPEC_PATH.relative_to(REPO_ROOT)} is not valid YAML: {exc}")
        return 1

    from openapi_spec_validator import (
        validate,
    )
    from openapi_spec_validator.readers import read_from_filename

    spec, base_uri = read_from_filename(str(SPEC_PATH))
    try:
        validate(spec, base_uri=base_uri)
    except Exception as exc:  # noqa: BLE001 — the validator raises several types
        print(f"ERROR: {SPEC_PATH.relative_to(REPO_ROOT)} failed spec validation: {exc}")
        return 1

    print(f"openapi spec valid, no duplicate keys ({len(spec.get('paths', {}))} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
