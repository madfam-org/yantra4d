"""Tests for the ceq coverage driver + tracker.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests -q

Everything network-facing is mocked. The three payload-mapping cases use REAL
manifests + REAL catalog entries from this repo — a synthetic fixture would
happily pass while the actual commons shape drifted underneath it. The chosen
cartridges are deliberately diverse:

  - ``aerator-cache``  — CadQuery, rich hyperobject block, part colours
  - ``julia-vase``     — OpenSCAD, a different engine lineage
  - ``flange-plate``   — graph cartridge (.graph.json), the newest kernel

If any of those is withdrawn from the commons the test skips rather than fails:
this suite pins the *mapping*, not the catalogue's membership.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from lib import ceq_coverage_core as core  # noqa: E402

sys.path.insert(0, str(REPO / "scripts" / "dev"))
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import ceq_backfill  # noqa: E402
import ceq_coverage  # noqa: E402

DIVERSE_SLUGS = ["aerator-cache", "julia-vase", "flange-plate"]


# ──────────────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def real_catalog():
    return core.load_catalog(core.CATALOG_PATH)


def _entry(catalog, slug):
    for c in catalog["cartridges"]:
        if c.get("slug") == slug:
            return c
    pytest.skip(f"{slug} is no longer in the commons catalog")


def _write_catalog(path: Path, slugs, **overrides):
    cartridges = []
    for slug in slugs:
        entry = {
            "slug": slug,
            "name": f"Name {slug}",
            "domain": "household",
            "engines": ["cadquery"],
            "commons_license": "CERN-OHL-W-2.0",
            "cdg_interfaces": [{"id": "i1"}],
            "standards": ["M22x1"],
        }
        entry.update(overrides)
        cartridges.append(entry)
    path.write_text(json.dumps({"schema_version": "commons_catalog_v1",
                                "cartridges": cartridges}), encoding="utf-8")
    return path


def _write_sidecar(path: Path, assets):
    doc = core.empty_sidecar()
    doc["assets"] = assets
    path.write_text(core.serialize_sidecar(doc), encoding="utf-8")
    return path


def _record(payload_hash="ph", url="https://cdn.ceq.lol/a.png"):
    return {
        "url": url,
        "hash": "content-hash",
        "rendered_at": "2026-08-24T00:00:00Z",
        "template": "hyperobject-card",
        "template_version": "1",
        "payload_hash": payload_hash,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 1. Payload mapping from three real, diverse manifests
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("slug", DIVERSE_SLUGS)
def test_card_payload_from_real_cartridge(real_catalog, slug):
    entry = _entry(real_catalog, slug)
    manifest = core.load_manifest(slug)
    data = core.card_payload(entry, manifest)

    assert data["slug"] == slug
    assert data["title"] and len(data["title"]) <= 61  # 60 + ellipsis
    # Accent is always present and always a hex colour — the card renderer
    # takes accent unconditionally.
    assert core._HEX_RE.match(data["accent"]), data["accent"]
    # Never emit empty-string optionals: an absent key and "" hash differently.
    assert all(v != "" for v in data.values())
    if "description" in data:
        assert len(data["description"]) <= 221


@pytest.mark.parametrize("slug", DIVERSE_SLUGS)
def test_texture_payload_from_real_cartridge(real_catalog, slug):
    entry = _entry(real_catalog, slug)
    data = core.texture_payload(entry, core.load_manifest(slug))
    assert data["slug"] == slug
    assert data["subject"]
    assert core._HEX_RE.match(data["accent"])
    if "standards" in data:
        assert data["standards"] == sorted(data["standards"])
        assert len(data["standards"]) <= 4


def test_card_payload_carries_the_hyperobject_block(real_catalog):
    """cdg_interfaces count + commons_license as provenance — the fields that
    make this a commons card rather than a generic thumbnail."""
    entry = _entry(real_catalog, "aerator-cache")
    data = core.card_payload(entry, core.load_manifest("aerator-cache"))
    ho = data["hyperobject"]
    assert ho["cdg_interfaces"] == len(entry["cdg_interfaces"])
    assert ho["provenance"] == entry["commons_license"]
    assert data["badge"] == entry["commons_license"]


def test_card_payload_omits_hyperobject_when_there_is_nothing_to_say():
    entry = {"slug": "bare", "name": "Bare", "domain": "household"}
    data = core.card_payload(entry, {})
    assert "hyperobject" not in data
    assert "badge" not in data
    assert "description" not in data


def test_accent_prefers_manifest_colour_over_domain():
    entry = {"slug": "x", "name": "X", "domain": "medical"}
    manifest = {"parts": [{"id": "a"}, {"id": "b", "default_color": "#AbCdEf"}]}
    assert core.card_payload(entry, manifest)["accent"] == "#abcdef"
    # Without a manifest colour it falls back to the domain accent.
    assert core.card_payload(entry, {})["accent"] == core.DOMAIN_ACCENT["medical"]
    # Unknown domain → neutral fallback, never a crash.
    assert core.card_payload({"slug": "x", "name": "X", "domain": "zzz"}, {})["accent"] == (
        core.FALLBACK_ACCENT
    )


def test_accent_ignores_non_hex_part_colours():
    manifest = {"parts": [{"default_color": "rebeccapurple"}, {"default_color": "#123456"}]}
    assert core.manifest_accent(manifest) == "#123456"
    assert core.manifest_accent({"parts": [{"default_color": "nope"}]}) is None


def test_i18n_blobs_are_flattened_to_english():
    entry = {"slug": "x", "name": {"en": "English", "es": "Espanol"}, "domain": "household"}
    assert core.card_payload(entry, {})["title"] == "English"
    # Spanish-only still yields text rather than an empty title.
    assert core.card_payload({"slug": "y", "name": {"es": "Solo"}}, {})["title"] == "Solo"


def test_no_silhouette_is_emitted(real_catalog):
    """Placeholder SVGs carry a generic per-geometry_type glyph, not an outline
    of the object; encoding one as a silhouette would bake a false claim into a
    content-addressed asset. Pinned so it is a decision, not an oversight."""
    for slug in DIVERSE_SLUGS:
        entry = _entry(real_catalog, slug)
        assert "silhouette" not in core.card_payload(entry, core.load_manifest(slug))


def test_missing_manifest_is_not_fatal(real_catalog):
    entry = _entry(real_catalog, "aerator-cache")
    assert core.load_manifest("this-slug-does-not-exist") == {}
    assert core.card_payload(entry, core.load_manifest("this-slug-does-not-exist"))["slug"]


# ──────────────────────────────────────────────────────────────────────────────
# 2. Payload hash — the resume primitive
# ──────────────────────────────────────────────────────────────────────────────

def test_payload_hash_matches_ceqs_recipe():
    """Recomputed byte-for-byte the way ceq's render_hash does it
    (ceq apps/api/src/ceq_api/render/hash.py). Drift here silently breaks
    resume, so the recipe is pinned literally rather than by import."""
    import hashlib

    data = {"b": 2, "a": 1}
    expected = hashlib.sha256(
        json.dumps({"template": "t", "version": "1", "data": data},
                   sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    assert core.payload_hash("t", data, "1") == expected


def test_payload_hash_is_key_order_independent():
    assert core.payload_hash("t", {"a": 1, "b": 2}, "1") == core.payload_hash(
        "t", {"b": 2, "a": 1}, "1"
    )


def test_payload_hash_changes_with_template_version():
    data = {"a": 1}
    assert core.payload_hash("t", data, "1") != core.payload_hash("t", data, "2")
    assert core.payload_hash("t", data, "1") != core.payload_hash("u", data, "1")


# ──────────────────────────────────────────────────────────────────────────────
# 3. Sidecar round-trip, determinism, validation
# ──────────────────────────────────────────────────────────────────────────────

def test_sidecar_round_trip(tmp_path):
    path = tmp_path / "ceq-coverage.json"
    doc = core.empty_sidecar()
    core.upsert_record(doc, "zeta", "card", _record())
    core.upsert_record(doc, "alpha", "texture", _record())
    core.write_sidecar(doc, path)

    back = core.load_sidecar(path)
    assert back["schema_version"] == core.SIDECAR_SCHEMA_VERSION
    assert core.sidecar_record(back, "zeta", "card")["url"] == _record()["url"]
    assert core.sidecar_record(back, "alpha", "texture") is not None


def test_sidecar_serialization_is_deterministic_and_sorted(tmp_path):
    a = core.empty_sidecar()
    core.upsert_record(a, "zeta", "texture", _record())
    core.upsert_record(a, "alpha", "card", _record())

    b = core.empty_sidecar()
    core.upsert_record(b, "alpha", "card", _record())
    core.upsert_record(b, "zeta", "texture", _record())

    assert core.serialize_sidecar(a) == core.serialize_sidecar(b)
    text = core.serialize_sidecar(a)
    assert text.index('"alpha"') < text.index('"zeta"')
    assert text.endswith("\n")
    # Re-serializing a loaded document is a no-op — a no-op backfill must not
    # produce a diff.
    path = tmp_path / "s.json"
    path.write_text(text, encoding="utf-8")
    assert core.serialize_sidecar(core.load_sidecar(path)) == text


def test_absent_sidecar_is_empty_not_an_error(tmp_path):
    doc = core.load_sidecar(tmp_path / "nope.json")
    assert doc["assets"] == {}


@pytest.mark.parametrize(
    "bad",
    [
        "[]",
        '{"schema_version": "wrong", "assets": {}}',
        '{"schema_version": "ceq_coverage_v1"}',
        '{"schema_version": "ceq_coverage_v1", "assets": []}',
        '{"schema_version": "ceq_coverage_v1", "assets": {"s": "not-an-object"}}',
        '{"schema_version": "ceq_coverage_v1", "assets": {"s": {"poster": {}}}}',
        '{"schema_version": "ceq_coverage_v1", "assets": {"s": {"card": {"url": "u"}}}}',
        '{"schema_version": "ceq_coverage_v1", "assets": {"s": {"card": '
        '{"url": 1, "hash": "h", "rendered_at": "t"}}}}',
        "{not json",
    ],
)
def test_malformed_sidecar_raises(tmp_path, bad):
    path = tmp_path / "s.json"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(core.CoverageError):
        core.load_sidecar(path)


# ──────────────────────────────────────────────────────────────────────────────
# 4. Resume-skip logic
# ──────────────────────────────────────────────────────────────────────────────

def test_needs_render_skips_matching_payload_hash():
    doc = core.empty_sidecar()
    core.upsert_record(doc, "s", "card", _record(payload_hash="abc"))
    assert core.needs_render(doc, "s", "card", "abc") is False
    assert core.needs_render(doc, "s", "card", "different") is True
    assert core.needs_render(doc, "s", "texture", "abc") is True
    assert core.needs_render(doc, "other", "card", "abc") is True


def test_record_without_payload_hash_is_re_rendered():
    """A hand-written or legacy record is healed rather than trusted — ceq's
    cache makes the re-render free."""
    doc = core.empty_sidecar()
    stale = _record()
    stale.pop("payload_hash")
    core.upsert_record(doc, "s", "card", stale)
    assert core.needs_render(doc, "s", "card", "abc") is True


def test_build_plan_skips_covered_and_keeps_the_rest(tmp_path, real_catalog):
    entries = core.catalog_entries(real_catalog)[:3]
    templates = dict(core.DEFAULT_TEMPLATES)
    versions = {templates["card"]: "1"}

    empty = core.empty_sidecar()
    full_plan = ceq_backfill.build_plan(entries, empty, ["card"], templates, versions)
    assert len(full_plan) == 3

    # Record the first item exactly as the driver would, then re-plan.
    doc = core.empty_sidecar()
    first = full_plan[0]
    core.upsert_record(doc, first["slug"], "card", _record(payload_hash=first["payload_hash"]))
    resumed = ceq_backfill.build_plan(entries, doc, ["card"], templates, versions)
    assert [p["slug"] for p in resumed] == [p["slug"] for p in full_plan[1:]]

    # A template-version bump invalidates the skip.
    bumped = ceq_backfill.build_plan(entries, doc, ["card"], templates, {templates["card"]: "2"})
    assert len(bumped) == 3


# ──────────────────────────────────────────────────────────────────────────────
# 5. Dry-run behaviour (no HTTP, exit 0)
# ──────────────────────────────────────────────────────────────────────────────

def _no_creds(monkeypatch):
    for var in ("JANUA_ISSUER", "CEQ_COVERAGE_CLIENT_ID", "CEQ_COVERAGE_CLIENT_SECRET"):
        monkeypatch.delenv(var, raising=False)


def _explode(*a, **k):  # pragma: no cover - only runs if the test fails
    raise AssertionError("no HTTP call may happen in dry-run")


def test_dry_run_without_credentials_exits_zero_and_makes_no_calls(
    tmp_path, monkeypatch, capsys
):
    _no_creds(monkeypatch)
    monkeypatch.setattr(ceq_backfill, "_request", _explode)
    catalog = _write_catalog(tmp_path / "cat.json", ["a", "b"])
    sidecar = tmp_path / "side.json"

    rc = ceq_backfill.main(
        ["--catalog", str(catalog), "--sidecar", str(sidecar), "--kinds", "card"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "dry run" in out and "no credentials in env" in out
    assert "2 render(s) planned" in out
    # Dry-run never writes the sidecar.
    assert not sidecar.exists()


def test_explicit_dry_run_with_credentials_still_makes_no_calls(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("JANUA_ISSUER", "https://janua.example")
    monkeypatch.setenv("CEQ_COVERAGE_CLIENT_ID", "id")
    monkeypatch.setenv("CEQ_COVERAGE_CLIENT_SECRET", "secret")
    monkeypatch.setattr(ceq_backfill, "_request", _explode)
    catalog = _write_catalog(tmp_path / "cat.json", ["a"])

    rc = ceq_backfill.main(
        ["--catalog", str(catalog), "--sidecar", str(tmp_path / "s.json"),
         "--dry-run", "--show-payload", "--kinds", "card"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "--dry-run" in out
    assert '"template": "hyperobject-card"' in out


def test_dry_run_respects_limit_and_only(tmp_path, monkeypatch, capsys):
    _no_creds(monkeypatch)
    catalog = _write_catalog(tmp_path / "cat.json", ["a", "b", "c"])
    args = ["--catalog", str(catalog), "--sidecar", str(tmp_path / "s.json"), "--kinds", "card"]

    assert ceq_backfill.main([*args, "--limit", "2"]) == 0
    assert "2 render(s) planned" in capsys.readouterr().out

    assert ceq_backfill.main([*args, "--only", "b"]) == 0
    out = capsys.readouterr().out
    assert "1 render(s) planned" in out and "plan b card" in out


def test_unknown_only_slug_fails(tmp_path, monkeypatch, capsys):
    _no_creds(monkeypatch)
    catalog = _write_catalog(tmp_path / "cat.json", ["a"])
    rc = ceq_backfill.main(
        ["--catalog", str(catalog), "--sidecar", str(tmp_path / "s.json"), "--only", "ghost"]
    )
    assert rc == 1
    assert "not in the catalog" in capsys.readouterr().err


def test_malformed_sidecar_fails_the_backfill_too(tmp_path, monkeypatch, capsys):
    _no_creds(monkeypatch)
    catalog = _write_catalog(tmp_path / "cat.json", ["a"])
    sidecar = tmp_path / "s.json"
    sidecar.write_text('{"schema_version": "nope"}', encoding="utf-8")
    rc = ceq_backfill.main(["--catalog", str(catalog), "--sidecar", str(sidecar)])
    assert rc == 1
    assert "FAILED" in capsys.readouterr().err


def test_rate_is_clamped_to_the_polite_ceiling(tmp_path, monkeypatch, capsys):
    _no_creds(monkeypatch)
    catalog = _write_catalog(tmp_path / "cat.json", ["a"])
    rc = ceq_backfill.main(
        ["--catalog", str(catalog), "--sidecar", str(tmp_path / "s.json"), "--rate", "6000"]
    )
    assert rc == 0
    assert "clamping" in capsys.readouterr().err


def test_rate_limiter_spaces_calls():
    """60/min == one call per second. The clock starts at 0.0 deliberately: a
    monotonic clock can read 0.0, and a falsy `_last` sentinel used to skip the
    very first spacing interval."""
    slept = []
    now = [0.0]
    limiter = ceq_backfill.RateLimiter(60, sleep=slept.append, clock=lambda: now[0])

    limiter.wait()          # first call is free
    assert slept == []
    limiter.wait()          # no time has passed → wait the full interval
    assert len(slept) == 1 and abs(slept[0] - 1.0) < 1e-9

    now[0] = 5.0            # plenty of time has passed → no wait
    limiter.wait()
    assert len(slept) == 1


def test_rate_limiter_zero_disables_spacing():
    slept = []
    limiter = ceq_backfill.RateLimiter(0, sleep=slept.append, clock=lambda: 0.0)
    assert limiter.interval == 0.0
    limiter.wait()
    limiter.wait()
    assert slept == []


# ──────────────────────────────────────────────────────────────────────────────
# 6. The render path with HTTP mocked
# ──────────────────────────────────────────────────────────────────────────────

class _FakeClient:
    def __init__(self, fail_slugs=()):
        self.calls = []
        self.fail_slugs = set(fail_slugs)

    def render_card(self, template, data):
        self.calls.append((template, data))
        if data["slug"] in self.fail_slugs:
            raise ceq_backfill.BackfillError("boom")
        return {
            "url": f"https://cdn.ceq.lol/{data['slug']}.png",
            "storage_uri": f"r2://ceq-assets/{data['slug']}.png",
            "hash": "content" + data["slug"],
            "template": template,
            "template_version": "1",
            "content_type": "image/png",
            "cached": False,
        }


def test_run_backfill_writes_records_and_is_idempotent(tmp_path, real_catalog):
    entries = core.catalog_entries(real_catalog)[:2]
    templates = dict(core.DEFAULT_TEMPLATES)
    versions = {templates["card"]: "1"}
    sidecar_path = tmp_path / "s.json"
    doc = core.empty_sidecar()
    plan = ceq_backfill.build_plan(entries, doc, ["card"], templates, versions)

    client = _FakeClient()
    rendered, failed = ceq_backfill.run_backfill(
        client, plan, doc, sidecar_path, rate=ceq_backfill.RateLimiter(0)
    )
    assert (rendered, failed) == (2, 0)
    assert sidecar_path.exists()

    written = core.load_sidecar(sidecar_path)
    rec = core.sidecar_record(written, entries[0]["slug"], "card")
    assert rec["url"].endswith(".png")
    assert rec["payload_hash"] == plan[0]["payload_hash"]
    assert rec["rendered_at"].endswith("Z")
    assert rec["storage_uri"].startswith("r2://")

    # Second pass over the same catalog has nothing left to do.
    assert ceq_backfill.build_plan(entries, written, ["card"], templates, versions) == []


def test_run_backfill_reports_failures_without_losing_successes(tmp_path, real_catalog):
    entries = core.catalog_entries(real_catalog)[:3]
    templates = dict(core.DEFAULT_TEMPLATES)
    doc = core.empty_sidecar()
    plan = ceq_backfill.build_plan(entries, doc, ["card"], templates, {templates["card"]: "1"})
    client = _FakeClient(fail_slugs=[plan[1]["slug"]])

    rendered, failed = ceq_backfill.run_backfill(
        client, plan, doc, tmp_path / "s.json", rate=ceq_backfill.RateLimiter(0)
    )
    assert (rendered, failed) == (2, 1)
    written = core.load_sidecar(tmp_path / "s.json")
    assert core.sidecar_record(written, plan[1]["slug"], "card") is None
    assert core.sidecar_record(written, plan[0]["slug"], "card") is not None


def test_token_is_cached_and_re_minted_before_expiry(monkeypatch):
    client = ceq_backfill.CeqClient("https://api.ceq.lol", "https://janua", "id", "sec")
    mints = []

    def fake_request(url, *, data, headers, timeout, method="GET"):
        mints.append(url)
        return {"access_token": f"tok{len(mints)}", "expires_in": 3600}

    monkeypatch.setattr(ceq_backfill, "_request", fake_request)
    assert client.token() == "tok1"
    assert client.token() == "tok1"  # cached
    assert len(mints) == 1

    # Push the cached expiry inside the refresh skew — the next call re-mints.
    client._token_exp = __import__("time").time() + 5
    assert client.token() == "tok2"
    assert len(mints) == 2


def test_token_mint_failure_is_actionable(monkeypatch):
    client = ceq_backfill.CeqClient("https://api.ceq.lol", "https://janua", "id", "sec")

    def fake_request(*a, **k):
        raise ceq_backfill.BackfillError("HTTP 401 from https://janua")

    monkeypatch.setattr(ceq_backfill, "_request", fake_request)
    with pytest.raises(ceq_backfill.BackfillError, match="CEQ_COVERAGE_CLIENT_ID"):
        client.token()


def test_template_versions_are_read_from_ceq(monkeypatch):
    client = ceq_backfill.CeqClient("https://api.ceq.lol", "https://janua", "id", "sec")
    monkeypatch.setattr(client, "token", lambda: "tok")
    monkeypatch.setattr(
        ceq_backfill,
        "_request",
        lambda *a, **k: [
            {"name": "hyperobject-card", "version": "3"},
            {"name": "card-standard", "version": "1"},
        ],
    )
    assert client.template_versions()["hyperobject-card"] == "3"


def test_unknown_template_fails_before_any_render(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JANUA_ISSUER", "https://janua.example")
    monkeypatch.setenv("CEQ_COVERAGE_CLIENT_ID", "id")
    monkeypatch.setenv("CEQ_COVERAGE_CLIENT_SECRET", "secret")
    monkeypatch.setattr(
        ceq_backfill.CeqClient, "template_versions", lambda self: {"card-standard": "1"}
    )
    monkeypatch.setattr(
        ceq_backfill.CeqClient,
        "render_card",
        lambda *a, **k: pytest.fail("must not render against an unknown template"),
    )
    catalog = _write_catalog(tmp_path / "cat.json", ["a"])
    rc = ceq_backfill.main(
        ["--catalog", str(catalog), "--sidecar", str(tmp_path / "s.json"), "--kinds", "card"]
    )
    assert rc == 1
    assert "does not serve template" in capsys.readouterr().err


def test_template_name_is_configurable(tmp_path, monkeypatch, capsys):
    _no_creds(monkeypatch)
    catalog = _write_catalog(tmp_path / "cat.json", ["a"])
    rc = ceq_backfill.main(
        ["--catalog", str(catalog), "--sidecar", str(tmp_path / "s.json"),
         "--kinds", "card", "--card-template", "hyperobject-card-v2"]
    )
    assert rc == 0
    assert "template=hyperobject-card-v2" in capsys.readouterr().out


# ──────────────────────────────────────────────────────────────────────────────
# 7. Thumbnail classification
# ──────────────────────────────────────────────────────────────────────────────

def test_thumbnail_status_sniffs_content_not_extension(tmp_path):
    d = tmp_path / "projects"
    d.mkdir()
    (d / "real.webp").write_bytes(b"RIFF\x00\x00\x00\x00WEBPVP8 rest")
    (d / "realpng.png").write_bytes(b"\x89PNG\r\n\x1a\nrest")
    # The placeholder generator's --emit-webp-names mode: SVG bytes, .webp name.
    (d / "fake.webp").write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>')
    (d / "tile.svg").write_bytes(b"<svg></svg>")

    dirs = (d,)
    assert core.thumbnail_status("real", dirs) == "real"
    assert core.thumbnail_status("realpng", dirs) == "real"
    assert core.thumbnail_status("fake", dirs) == "placeholder"
    assert core.thumbnail_status("tile", dirs) == "placeholder"
    assert core.thumbnail_status("absent", dirs) == "missing"


def test_real_raster_wins_over_a_leftover_placeholder(tmp_path):
    d = tmp_path / "projects"
    d.mkdir()
    (d / "both.svg").write_bytes(b"<svg></svg>")
    (d / "both.png").write_bytes(b"\x89PNG\r\n\x1a\nrest")
    assert core.thumbnail_status("both", (d,)) == "real"


# ──────────────────────────────────────────────────────────────────────────────
# 8. Tracker output shapes
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def tracker_fixture(tmp_path):
    catalog = _write_catalog(tmp_path / "cat.json", ["alpha", "beta", "gamma"])
    thumbs = tmp_path / "projects"
    thumbs.mkdir()
    (thumbs / "alpha.webp").write_bytes(b"RIFF\x00\x00\x00\x00WEBPVP8 x")
    (thumbs / "beta.svg").write_bytes(b"<svg></svg>")
    # gamma has no thumbnail at all
    sidecar = _write_sidecar(
        tmp_path / "side.json",
        {"alpha": {"card": _record()}, "beta": {"card": _record(), "texture": _record()}},
    )
    return catalog, sidecar, (thumbs,)


def test_compute_report_shape(tracker_fixture):
    catalog, sidecar, thumbs = tracker_fixture
    report = ceq_coverage.compute(catalog, sidecar, thumbs)

    assert report["total_cartridges"] == 3
    assert report["kinds"]["card"]["covered"] == 2
    assert report["kinds"]["card"]["missing"] == ["gamma"]
    assert report["kinds"]["texture"]["covered"] == 1
    assert sorted(report["kinds"]["texture"]["missing"]) == ["alpha", "gamma"]
    assert report["complete"] == 1  # only beta has both
    assert report["thumbnails"] == {"real": 1, "placeholder": 1, "missing": 1}
    # gamma is missing a card AND has no thumbnail → the no-thumbnail cohort.
    assert report["cohorts"]["card"]["missing"] == 1
    assert report["cohorts"]["texture"]["real"] == 1  # alpha: real thumb, no texture
    assert report["orphans"] == []


def test_orphan_sidecar_slugs_are_reported(tmp_path):
    catalog = _write_catalog(tmp_path / "cat.json", ["alpha"])
    sidecar = _write_sidecar(
        tmp_path / "s.json", {"alpha": {"card": _record()}, "withdrawn": {"card": _record()}}
    )
    report = ceq_coverage.compute(catalog, sidecar, ())
    assert report["orphans"] == ["withdrawn"]


def test_tracker_prints_one_line_summary(tracker_fixture, monkeypatch, capsys):
    catalog, sidecar, thumbs = tracker_fixture
    monkeypatch.setattr(core, "THUMB_DIRS", thumbs)
    monkeypatch.setattr(
        sys, "argv", ["ceq_coverage.py", "--catalog", str(catalog), "--sidecar", str(sidecar)]
    )
    assert ceq_coverage.main() == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("ceq coverage: 2/3 card, 1/3 texture — 1/3 complete")
    assert "gallery thumbnails:" in lines[1]


def test_tracker_json_mode(tracker_fixture, monkeypatch, capsys):
    catalog, sidecar, thumbs = tracker_fixture
    monkeypatch.setattr(core, "THUMB_DIRS", thumbs)
    monkeypatch.setattr(
        sys,
        "argv",
        ["ceq_coverage.py", "--catalog", str(catalog), "--sidecar", str(sidecar), "--json"],
    )
    assert ceq_coverage.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_cartridges"] == 3
    assert payload["kinds"]["card"]["covered"] == 2


def test_tracker_never_fails_on_missing_coverage(tmp_path, monkeypatch, capsys):
    """The informational lane: 0/N is the expected state until the backfill
    runs, so it must exit 0."""
    catalog = _write_catalog(tmp_path / "cat.json", ["a", "b"])
    monkeypatch.setattr(core, "THUMB_DIRS", ())
    monkeypatch.setattr(
        sys,
        "argv",
        ["ceq_coverage.py", "--catalog", str(catalog), "--sidecar", str(tmp_path / "absent.json")],
    )
    assert ceq_coverage.main() == 0
    out = capsys.readouterr().out
    assert "0/2 card" in out and "no sidecar yet" in out


def test_tracker_fails_on_malformed_sidecar(tmp_path, monkeypatch, capsys):
    catalog = _write_catalog(tmp_path / "cat.json", ["a"])
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version": "ceq_coverage_v1", "assets": {"a": {"card": {}}}}',
                   encoding="utf-8")
    monkeypatch.setattr(core, "THUMB_DIRS", ())
    monkeypatch.setattr(
        sys, "argv", ["ceq_coverage.py", "--catalog", str(catalog), "--sidecar", str(bad)]
    )
    assert ceq_coverage.main() == 1
    assert "FAILED" in capsys.readouterr().err


def test_tracker_strict_and_min_coverage_gates(tracker_fixture, monkeypatch, capsys):
    catalog, sidecar, thumbs = tracker_fixture
    monkeypatch.setattr(core, "THUMB_DIRS", thumbs)
    base = ["ceq_coverage.py", "--catalog", str(catalog), "--sidecar", str(sidecar)]

    monkeypatch.setattr(sys, "argv", [*base, "--strict"])
    assert ceq_coverage.main() == 1
    assert "--strict" in capsys.readouterr().err

    monkeypatch.setattr(sys, "argv", [*base, "--min-coverage", "50"])
    assert ceq_coverage.main() == 1  # texture is at 33%

    monkeypatch.setattr(sys, "argv", [*base, "--min-coverage", "30"])
    assert ceq_coverage.main() == 0


def test_tracker_list_missing(tracker_fixture, monkeypatch, capsys):
    catalog, sidecar, thumbs = tracker_fixture
    monkeypatch.setattr(core, "THUMB_DIRS", thumbs)
    monkeypatch.setattr(
        sys,
        "argv",
        [*["ceq_coverage.py", "--catalog", str(catalog), "--sidecar", str(sidecar)],
         "--list-missing", "card"],
    )
    assert ceq_coverage.main() == 0
    assert "MISSING card gamma" in capsys.readouterr().out


# ──────────────────────────────────────────────────────────────────────────────
# 9. The real catalog is read dynamically
# ──────────────────────────────────────────────────────────────────────────────

def test_counts_come_from_the_catalog_on_disk(real_catalog):
    """No cartridge count is baked into these scripts — the commons is growing
    (a fourth-hundred merge is in flight) and a literal would go stale."""
    report = ceq_coverage.compute(core.CATALOG_PATH, core.SIDECAR_PATH)
    assert report["total_cartridges"] == len(core.catalog_entries(real_catalog))
    assert report["total_cartridges"] > 0


def test_malformed_catalog_raises(tmp_path):
    bad = tmp_path / "cat.json"
    bad.write_text('{"schema_version": "commons_catalog_v1"}', encoding="utf-8")
    with pytest.raises(core.CoverageError, match="cartridges"):
        core.load_catalog(bad)
    missing = tmp_path / "nope.json"
    with pytest.raises(core.CoverageError, match="not found"):
        core.load_catalog(missing)
