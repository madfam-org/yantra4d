"""Tests for the CDG compatibility graph derivation + endpoints.

Uses the `_isolate_config` autouse fixture (conftest) to point CARTRIDGES_DIRS at a
tmp_path; each test writes only the manifests it needs. The module cache is dropped in
setup.
"""
import json

import pytest

from services.core.compatibility_graph import (
    get_graph,
    invalidate_graph,
    normalize_family,
    works_with,
)


@pytest.fixture(autouse=True)
def _fresh_graph():
    invalidate_graph()
    yield
    invalidate_graph()


def _write(tmp_path, slug, interfaces, *, domain="industrial", unlisted=False):
    """Write a manifest whose hyperobject.cdg_interfaces = the given list."""
    d = tmp_path / slug
    d.mkdir(exist_ok=True)
    manifest = {
        "project": {"slug": slug, "name": slug.title(), "unlisted": unlisted},
        "hyperobject": {
            "is_hyperobject": True,
            "domain": domain,
            "cdg_interfaces": interfaces,
        },
    }
    (d / "project.json").write_text(json.dumps(manifest))
    return d


def _iface(geometry_type, standard, label="iface"):
    return {"id": standard, "label": label, "geometry_type": geometry_type,
            "standard": standard, "parameters": []}


# ── normalization ─────────────────────────────────────────────────────────────
def test_normalize_family_variants_collapse():
    # different free-text strings for the same family collapse to one key
    assert normalize_family("ASME B1.1 1/4-20 UNC") == "unc-1/4-20"
    assert normalize_family("ASME 1/4-20") == "unc-1/4-20"
    assert normalize_family("VESA MIS-D/E/F (FDMI)") == "vesa"
    assert normalize_family("Gridfinity (42mm module, 7mm Z-unit)") == "gridfinity"
    assert normalize_family("NEMA 17/23/34") == "nema-stepper"


def test_normalize_family_internal_and_unknown():
    assert normalize_family("internal") is None
    assert normalize_family("") is None
    assert normalize_family("something totally bespoke xyz") is None


def test_normalize_family_internal_prefixed_variants_rejected():
    # bespoke internals must not leak into shared families however they're suffixed
    assert normalize_family("internal solids 40mm") is None
    assert normalize_family("internal peg grid 8mm") is None
    assert normalize_family("internal/aocl") is None
    # a real standard must not hide behind the prefix — manifests say it plainly
    assert normalize_family("internal (D-shaft / spline)") is None
    assert normalize_family("D-shaft / spline bore") == "shaft-spline"


def test_normalize_family_pco_hyphen_and_spi_neck():
    # hyphenated PCO spelling joins the existing family; SPI necks are their own family
    assert normalize_family("28mm/bottle (28-410 / PCO-1881)") == "pco-1881"
    assert normalize_family("PCO 1881 neck") == "pco-1881"
    assert normalize_family("SPI 20-410 / 24-410 / 28-410 (8 TPI)") == "spi-neck"


def test_normalize_family_drone_mount_split_from_led_matrix():
    # the FPV motor bolt square is not an LED matrix; WS2812 strings stay addressable
    assert normalize_family("16x16 / 19x19 / 9x9 brushless motor mount") == "drone-motor-mount"
    assert normalize_family("WS2812B 8x8 / 16x16 (~10 mm pitch)") == "addressable-led"


def test_normalize_family_pc_fan_needs_fan_context():
    assert normalize_family("PC fan 40-140mm") == "pc-fan"
    assert normalize_family("120 mm fan") == "pc-fan"
    assert normalize_family("52mm/60mm gauge") == "auto-gauge-52-60"
    assert normalize_family("solids 40mm") is None


def test_normalize_family_lab_and_optics():
    assert normalize_family("ANSI/SLAS 1-2004 & 4-2004 (9mm pitch)") == "slas-microplate"
    assert normalize_family("SBS 9mm pitch (small)") == "slas-microplate"
    assert normalize_family("single-channel micropipette (3.8-6.0 mm shaft)") is None
    assert normalize_family("ISO 8037-1:2003") == "microscope-slide"
    assert normalize_family("ISO 8036 immersion oil") is None
    assert normalize_family("15/50mL Falcon") == "conical-tube"
    assert normalize_family("3/16-1/4in tube") is None
    assert normalize_family("90mm petri") == "petri-90mm"
    assert normalize_family("150mm petri") is None
    assert normalize_family("PTFE stir bars 12/20/25/38/50 mm") == "stir-bar"
    assert normalize_family("stirrup pump") is None
    assert normalize_family("Luer barrel") == "luer"
    assert normalize_family("luerless taper") is None
    assert normalize_family("12 mm / 1/2 in support rod") == "support-rod-12"
    assert normalize_family("Ø1/2 in (12.7 mm) optical post") == "support-rod-12"
    assert normalize_family("12.7 mm (1/2 in) feeler blade") is None
    assert normalize_family("Ø1 in (25.4 mm) / Ø25 mm optic") == "optic-25.4"
    assert normalize_family("Ø2 in optic") is None


def test_normalize_family_construction_and_wall_systems():
    assert normalize_family("STEMFIE 4mm hole on 10mm pitch") == "stemfie"
    assert normalize_family("STEM kit") is None
    assert normalize_family("construction brick 8mm") == "brick-8mm-stud"
    assert normalize_family("masonry brick") is None
    assert normalize_family("1-inch pegboard / IKEA SKÅDIS") == "pegboard-1in"
    assert normalize_family("Pegboard 1 in / 6.35 mm") == "pegboard-1in"
    assert normalize_family("IKEA SKADIS board") is None  # 40mm system is NOT 1in pegboard
    assert normalize_family("French cleat 45 deg") == "french-cleat"
    assert normalize_family("boat cleat") is None
    assert normalize_family("Wall Keyhole") == "keyhole-hanger"
    assert normalize_family("standard key (Kwikset KW1 / Schlage SC1)") is None


def test_normalize_family_boards_and_electronics():
    assert normalize_family("RPi 40-pin form factor") == "rpi-mount"
    assert normalize_family("RPi HAT") == "rpi-mount"
    assert normalize_family("VL53/MPU6050/Pi-cam") is None  # sensor combo is bespoke
    assert normalize_family("Arduino form factors") == "arduino-mount"
    assert normalize_family("micro:bit edge connector") is None
    assert normalize_family("Omron SS/D2F") == "microswitch-d2f"
    assert normalize_family("generic micro switch") is None
    assert normalize_family("SG90/MG996R") == "servo-body"
    assert normalize_family("servo horn 25T") == "servo-spline"
    assert normalize_family("SMA / U.FL") == "sma-rf"
    assert normalize_family("small parts tray") is None
    assert normalize_family("FPV micro/nano cam (nano 14 / micro 19 / mini 21 mm)") == "fpv-cam"
    assert normalize_family("FPGA board") is None
    assert normalize_family("5050/2835 strip") == "led-strip"
    assert normalize_family("5050 aluminum channel") is None
    assert normalize_family("3.5mm AT switch") == "at-switch-3.5mm"
    assert normalize_family("3.5mm audio jack") is None
    assert normalize_family("SAE J1962") == "sae-j1962"
    assert normalize_family("SAE J1128 4/7-pin") is None  # wire spec, not the connector
    assert normalize_family("ISO 8820-3 ATO/Mini") == "ato-fuse"
    assert normalize_family("clarinet / alto / tenor mouthpiece (~30-36 mm)") is None


def test_normalize_family_machine_and_metrology():
    assert normalize_family("MGN9/12/15") == "mgn-rail"
    assert normalize_family("magnesium bracket") is None
    assert normalize_family("ISO 2904 (Tr) / ACME") == "trapezoidal-thread"
    assert normalize_family("trapeze bar") is None
    assert normalize_family("ISO 4183 (A/SPZ)") == "v-belt"
    assert normalize_family("belt sander") is None
    assert normalize_family("ISO 261 / ISO 965") == "iso-metric-thread"
    assert normalize_family("ISO 286 (shaft/hole tolerance)") is None  # tolerance spec, not a mate
    assert normalize_family("ER / straight-shank") == "er-collet"
    assert normalize_family("0-3 mm pin-vise collet") is None
    assert normalize_family("60 deg lever-indicator dovetail") == "indicator-dovetail"
    assert normalize_family("dovetail drawer joint") is None
    assert normalize_family("8 mm indicator stem (Mitutoyo Series 2)") == "indicator-stem-8mm"
    assert normalize_family("stem caster 3/8in") is None
    assert normalize_family("Kurt-style vise bolt pattern") == "kurt-vise"
    assert normalize_family("yogurt strainer") is None
    assert normalize_family("1/4 in hex driver bit (6.35 mm A/F)") == "hex-bit-1/4"
    assert normalize_family("drill bit 6mm") is None


def test_normalize_family_plumbing_and_household():
    assert normalize_family("PVC sched (nominal)") == "ips-pipe"
    assert normalize_family("1/2-3/4 in IPS stub slip (PVC sched 40)") == "ips-pipe"
    assert normalize_family("1/2in & 3/4in IPS pipe") == "ips-pipe"
    assert normalize_family("Copper / PEX OD 1/2-1 in") == "cts-pipe"  # CTS OD != IPS OD
    assert normalize_family("3/8-3/4 in tube barb") is None
    assert normalize_family("US tubular 1-1/4 / 1-1/2 in slip") == "tubular-drain"
    assert normalize_family("tube rack") is None
    assert normalize_family("US round duct 4/5/6 in") == "round-duct"
    assert normalize_family("US register 4x10/4x12/6x10/6x12 in") is None
    assert normalize_family("26mm crown cap") == "crown-cap-26"
    assert normalize_family("crown molding") is None
    assert normalize_family("US/EU wall box") == "wall-box"
    assert normalize_family("wall stud 16 in on-center") == "wall-stud"
    assert normalize_family("US/EU license plate (12x6in / 520x110mm)") == "license-plate"
    assert normalize_family("ISO/US plate") is None  # pre-D12 wording was too vague to map
    assert normalize_family("ANSI/BHMA A156.2 deadbolt strike, 1 in bore") == "ansi-a156-strike"
    assert normalize_family("standard strike (#8/#10 wood screw, ANSI A156.2 body)") == "ansi-a156-strike"
    assert normalize_family("A15 bulb") is None


def test_normalize_family_vehicle_and_outdoor():
    assert normalize_family("ISO handlebar 22.2/25.4/31.8") == "handlebar-clamp"
    assert normalize_family("handlebar 7/8-1in (22.2-25.4mm)") == "handlebar-clamp"
    assert normalize_family("3/4-1in tube") is None  # mobility tube range is not the bar standard
    assert normalize_family("water-bottle boss") == "bottle-cage-boss"
    assert normalize_family("PCO 1881 bottle") == "pco-1881"
    assert normalize_family("550 paracord (~4mm)") == "paracord-550"
    assert normalize_family("cord organizer") is None
    assert normalize_family("6/8mm ferro rod") == "ferro-rod"
    assert normalize_family("ferrous plate") is None


def test_normalize_family_craft_and_wearables():
    assert normalize_family("18/20/22mm lug") == "watch-lug"
    assert normalize_family("M12 lug nut") is None
    assert normalize_family("ETA 2824-2 (25.6 mm / 11.5 ligne)") == "watch-movement"
    assert normalize_family("ETA 30 minutes") is None
    assert normalize_family("Class 15 / L-style bobbin (6.1 mm bore, 20.3 mm OD)") == "bobbin-class-15"
    assert normalize_family("M-class bobbin") is None
    assert normalize_family("low / high shank (19 / 32 mm bar-to-plate)") == "presser-shank"
    assert normalize_family("Citadel/Vallejo/dropper") == "paint-pot"
    assert normalize_family("dropper bottle 30ml") is None
    assert normalize_family("business card") == "business-card"
    assert normalize_family("playing card") == "card-format"
    assert normalize_family("58/54/51mm basket") == "portafilter-58"
    assert normalize_family("58 mm hole saw") is None
    assert normalize_family("5/8-27 mic thread") == "mic-thread-5/8-27"
    assert normalize_family("microphone cable") is None
    assert normalize_family("5/8in (16mm) baby pin") == "baby-pin-5/8"
    assert normalize_family("baby bottle") is None
    assert normalize_family(
        "MOLLE/PALS MIL-W-17337 / A-A-55301 (1in rows, 1.5in columns)") == "molle-pals"
    # bare spec numbers stay unmapped: the manifest wording carries the family
    assert normalize_family("MIL-W-17337 / A-A-55301 (1in rows, 1.5in columns)") is None


# ── edge derivation ───────────────────────────────────────────────────────────
def test_bolt_pattern_self_mates(tmp_path):
    _write(tmp_path, "plate-a", [_iface("bolt_pattern", "ASME B1.1 1/4-20 UNC")])
    _write(tmp_path, "plate-b", [_iface("bolt_pattern", "ASME 1/4-20")])
    g = get_graph()
    assert g["edge_count"] == 1
    e = g["edges"][0]
    assert {e["a"], e["b"]} == {"plate-a", "plate-b"}
    assert e["kind"] == "mates_with"
    assert e["family"] == "unc-1/4-20"


def test_socket_thread_complementary_mate(tmp_path):
    _write(tmp_path, "bottle", [_iface("thread", "PCO 1881")])
    _write(tmp_path, "cap", [_iface("socket", "PCO 1881 neck")])
    g = get_graph()
    assert g["edge_count"] == 1
    assert g["edges"][0]["kind"] == "mates_with"
    assert g["edges"][0]["family"] == "pco-1881"


def test_grid_is_same_family_not_mates(tmp_path):
    _write(tmp_path, "bin", [_iface("grid", "Gridfinity 42mm")])
    _write(tmp_path, "base", [_iface("grid", "Gridfinity (42mm module)")])
    g = get_graph()
    assert g["edge_count"] == 1
    assert g["edges"][0]["kind"] == "same_family"


def test_no_edge_across_different_families(tmp_path):
    _write(tmp_path, "vesa-thing", [_iface("bolt_pattern", "VESA MIS-D")])
    _write(tmp_path, "nema-thing", [_iface("bolt_pattern", "NEMA 17")])
    assert get_graph()["edge_count"] == 0


def test_incompatible_geometry_same_family_no_edge(tmp_path):
    # two 'surface' interfaces of the same family don't mate (surface not self-mating)
    _write(tmp_path, "a", [_iface("surface", "VESA MIS-D")])
    _write(tmp_path, "b", [_iface("surface", "VESA MIS-D")])
    assert get_graph()["edge_count"] == 0


def test_internal_standard_ignored(tmp_path):
    _write(tmp_path, "a", [_iface("bolt_pattern", "internal")])
    _write(tmp_path, "b", [_iface("bolt_pattern", "internal")])
    g = get_graph()
    assert g["node_count"] == 0  # nothing with a real family
    assert g["edge_count"] == 0


def test_unlisted_excluded(tmp_path):
    _write(tmp_path, "shown", [_iface("bolt_pattern", "1/4-20")])
    _write(tmp_path, "hidden", [_iface("bolt_pattern", "1/4-20")], unlisted=True)
    g = get_graph()
    assert {n["slug"] for n in g["nodes"]} == {"shown"}
    assert g["edge_count"] == 0


def test_degree_and_hub_ordering(tmp_path):
    # a hub that mates with three leaves via the same family
    _write(tmp_path, "hub", [_iface("bolt_pattern", "1/4-20")])
    for leaf in ("leaf-a", "leaf-b", "leaf-c"):
        _write(tmp_path, leaf, [_iface("bolt_pattern", "1/4-20")])
    g = get_graph()
    # hub + 3 leaves all pairwise share the family → complete graph K4 = 6 edges
    assert g["edge_count"] == 6
    # every node degree 3
    assert all(n["degree"] == 3 for n in g["nodes"])


def test_works_with_groups_reasons(tmp_path):
    _write(tmp_path, "arca", [
        _iface("bolt_pattern", "ASME B1.1 1/4-20 UNC"),
        _iface("profile", "Arca-Swiss 38mm"),
    ])
    _write(tmp_path, "clamp", [_iface("socket", "Arca-Swiss clamp")])
    _write(tmp_path, "post", [_iface("bolt_pattern", "1/4-20")])
    w = works_with("arca")
    assert w["slug"] == "arca"
    partners = {p["slug"]: p for p in w["partners"]}
    # clamp mates via arca-swiss (socket↔profile); post mates via 1/4-20 (bolt↔bolt)
    assert "clamp" in partners and "post" in partners
    assert partners["clamp"]["reasons"][0]["family"] == "arca-swiss"
    assert partners["post"]["reasons"][0]["family"] == "unc-1/4-20"
    assert partners["clamp"]["thumbnail"] == "/projects/clamp.svg"


def test_caching_rebuilds_on_change(tmp_path):
    _write(tmp_path, "a", [_iface("bolt_pattern", "1/4-20")])
    assert get_graph()["node_count"] == 1
    _write(tmp_path, "b", [_iface("bolt_pattern", "1/4-20")])
    assert get_graph()["node_count"] == 2  # signature changed → rebuilt


# ── endpoints ─────────────────────────────────────────────────────────────────
def test_endpoints(tmp_path):
    _write(tmp_path, "plate-a", [_iface("bolt_pattern", "1/4-20")])
    _write(tmp_path, "plate-b", [_iface("bolt_pattern", "1/4-20")])
    from app import create_app
    client = create_app().test_client()

    r = client.get("/api/catalog/graph")
    assert r.status_code == 200
    assert r.get_json()["edge_count"] == 1

    r = client.get("/api/catalog/plate-a/works-with")
    assert r.status_code == 200
    body = r.get_json()
    assert body["count"] == 1
    assert body["partners"][0]["slug"] == "plate-b"

    r = client.get("/api/catalog/families")
    assert r.status_code == 200
    fams = r.get_json()["families"]
    assert any(f["family"] == "unc-1/4-20" for f in fams)
