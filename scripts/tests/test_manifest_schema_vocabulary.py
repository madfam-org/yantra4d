"""Tests for the hyperobject vocabulary the manifest schema actually enforces.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_manifest_schema_vocabulary.py -q

`test_validate_manifests.py` pins the validator's *classification* logic against
a stub schema. This module pins the opposite half: the REAL
`packages/schemas/project-manifest.schema.json`, and specifically the thing that
used to be true of it and no longer is.

The `hyperobject` block used to sit at the ROOT of the schema document, as a
sibling of `properties`. JSON Schema has no `hyperobject` keyword, so the whole
block was inert: every `domain` and every `geometry_type` in the commons passed
whatever it said, and four vocabulary values shipped that the enum never
declared. Moving the block under `properties` is what makes the enums real, so
the first test below asserts the LOCATION, not just the contents -- a future
edit that moves it back out would otherwise leave every other test here passing
while validating nothing.

The enum membership tests are deliberately value-by-value rather than a set
comparison: a set comparison fails as one opaque diff when a maintainer adds a
legitimate new value, whereas these say which value went missing.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO / "packages" / "schemas" / "project-manifest.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

#: Values Telesia's dual-screen and foldable device cartridges need (gate H6).
DEVICE_GEOMETRY_TYPES = ("hinge", "screen", "port")
#: Values already shipping in the commons before this vocabulary was declared.
IN_USE_GEOMETRY_TYPES = (
    "flange", "boss", "threaded_socket", "seal", "engraving", "polyhedron", "fem_mesh",
)
IN_USE_DOMAINS = (
    "wearable", "soft-robotics", "agriculture", "consumer", "construction",
    "electronics", "energy", "play",
)


def _hyperobject_schema():
    return SCHEMA["properties"]["hyperobject"]


def _geometry_enum():
    return _hyperobject_schema()["properties"]["cdg_interfaces"]["items"]["properties"][
        "geometry_type"
    ]["enum"]


def _domain_enum():
    return _hyperobject_schema()["properties"]["domain"]["enum"]


def manifest(hyperobject):
    """A minimally valid manifest carrying the given hyperobject block."""
    return {
        "project": {"name": "Fixture", "slug": "fixture", "version": "1.0.0"},
        "modes": [
            {
                "scad_file": "fixture.scad",
                "label": {"en": "Fixture"},
                "parts": ["body"],
                "estimate": {"base": 1},
            }
        ],
        "parts": {},
        "parameters": [],
        "hyperobject": hyperobject,
    }


def interface(geometry_type):
    return {
        "id": "device_hinge",
        "label": {"en": "Device hinge"},
        "geometry_type": geometry_type,
    }


def errors(instance):
    """Validation errors raised INSIDE the hyperobject block.

    Scoped on purpose: an unrelated fixture mistake elsewhere in the manifest
    would otherwise make every "this must be rejected" test below pass for the
    wrong reason. `test_the_base_fixture_is_otherwise_valid` guards the rest.
    """
    return [
        e
        for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(instance)
        if e.json_path.startswith("$.hyperobject")
    ]


def test_the_base_fixture_is_otherwise_valid():
    """If the fixture stops validating for unrelated reasons, say so here once
    rather than as a confusing failure in every vocabulary test."""
    all_errors = list(
        jsonschema.Draft202012Validator(SCHEMA).iter_errors(manifest({"domain": "medical"}))
    )
    assert not all_errors, [f"{e.json_path}: {e.message}" for e in all_errors]


# --- the regression this module exists for ---------------------------------

def test_hyperobject_is_a_validated_property_not_a_root_sibling():
    """The block must live under `properties`, or none of it is enforced."""
    assert "hyperobject" in SCHEMA["properties"], (
        "the hyperobject block is not under `properties` -- JSON Schema ignores "
        "unknown root keywords, so its enums validate nothing"
    )
    assert "hyperobject" not in SCHEMA, (
        "a root-level `hyperobject` key is an inert copy; there must be exactly one, "
        "under `properties`"
    )


def test_an_undeclared_geometry_type_is_rejected():
    bad = errors(manifest({"cdg_interfaces": [interface("wormhole")]}))
    assert bad, "an undeclared geometry_type must not validate"
    assert any("wormhole" in e.message for e in bad)


def test_an_undeclared_domain_is_rejected():
    bad = errors(manifest({"domain": "interplanetary"}))
    assert bad, "an undeclared domain must not validate"
    assert any("interplanetary" in e.message for e in bad)


# --- the vocabulary this PR adds -------------------------------------------

@pytest.mark.parametrize("geometry_type", DEVICE_GEOMETRY_TYPES)
def test_device_geometry_types_validate(geometry_type):
    assert geometry_type in _geometry_enum()
    assert not errors(manifest({"cdg_interfaces": [interface(geometry_type)]}))


def test_consumer_electronics_domain_validates():
    assert "consumer-electronics" in _domain_enum()
    assert not errors(manifest({"domain": "consumer-electronics"}))


# --- the vocabulary the commons was already using undeclared ---------------

@pytest.mark.parametrize("geometry_type", IN_USE_GEOMETRY_TYPES)
def test_geometry_types_already_in_the_commons_validate(geometry_type):
    """These shipped before the enum declared them; validating the block must
    not retroactively reject the cartridges that carry them."""
    assert geometry_type in _geometry_enum()
    assert not errors(manifest({"cdg_interfaces": [interface(geometry_type)]}))


@pytest.mark.parametrize("domain", IN_USE_DOMAINS)
def test_domains_already_in_the_commons_validate(domain):
    assert domain in _domain_enum()
    assert not errors(manifest({"domain": domain}))


def test_the_legacy_nested_domain_enum_matches_the_canonical_one():
    """`project.hyperobject.domain` is the older location for the same field.

    It drifted once already -- `infrastructure` was added to the canonical enum
    and not to this one -- which makes a cartridge's domain legal in one half of
    the manifest and illegal in the other.
    """
    nested = SCHEMA["properties"]["project"]["properties"]["hyperobject"]["properties"][
        "domain"
    ]["enum"]
    assert nested == _domain_enum()


# --- shapes the commons ships that validation must not break ---------------

def test_material_awareness_accepts_the_legacy_boolean():
    """flange-plate and spacer-block ship `material_awareness: true`.

    Cartridges are PRs to madfam-org/solid-hyperobjects, so tightening this to
    objects only would break the commons from a repo that cannot fix it.
    """
    assert not errors(manifest({"material_awareness": True}))
    assert not errors(manifest({"material_awareness": {"tolerance_by_material": True}}))


def test_unknown_keys_inside_the_hyperobject_block_are_tolerated():
    """`is_hyperobject`, `pilot_hyperobject`, `ontological_framework` and friends
    are carried by 24 cartridges. The block declares no `additionalProperties:
    false`, and must not start doing so without a commons migration."""
    assert not errors(
        manifest({"domain": "medical", "pilot_hyperobject": True, "is_hyperobject": True})
    )


def test_interface_id_pattern_still_bites():
    """Widening the geometry vocabulary must not widen anything else."""
    bad = errors(
        manifest({"cdg_interfaces": [{**interface("hinge"), "id": "Device-Hinge"}]})
    )
    assert bad, "interface ids are lower snake_case; the pattern must still apply"


def test_geometry_and_domain_enums_have_no_duplicates():
    for name, values in (("geometry_type", _geometry_enum()), ("domain", _domain_enum())):
        assert len(values) == len(set(values)), f"duplicate value in the {name} enum"


def test_every_enum_value_is_glossed_in_its_description():
    """Each vocabulary value carries a one-line gloss, so a contributor picking
    between `socket` and `threaded_socket` is not guessing."""
    geometry = _hyperobject_schema()["properties"]["cdg_interfaces"]["items"][
        "properties"
    ]["geometry_type"]
    missing = [v for v in geometry["enum"] if f"{v}:" not in geometry["description"]]
    assert not missing, f"geometry_type values with no gloss: {missing}"

    domain = _hyperobject_schema()["properties"]["domain"]
    undocumented = [v for v in domain["enum"] if v not in domain["description"]]
    assert not undocumented, f"domain values absent from the description: {undocumented}"
