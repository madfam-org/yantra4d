"""Tests for the value-extraction audit recomputation.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests -q

Two kinds of test live here.

The pure ones — formatting, the marker splice, the private-cartridge filter, the
partial-checkout guard — construct their own inputs and run everywhere, including
on a clone with no submodules initialised.

The measuring ones need the whole commons on disk. They ``skip`` when the
checkout is partial rather than assert over a commons that is missing 34
cartridges: a green assertion over an under-counted commons is exactly the
failure this script exists to prevent, so a partial run must not be able to
produce one. In the ``manifest-validation`` job the checkout is
``submodules: recursive`` and ``validate_manifests.py`` already fails a partial
one in the same job, so the skip cannot hide anything in CI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import value_extraction_audit as vea

# ──────────────────────────────────────────────────────────────────────────────
# fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def commons():
    """The published commons, or a skip if the submodule checkout is partial."""
    loaded = vea.load_commons()
    declared = json.loads(vea.CATALOG_JSON.read_text(encoding="utf-8"))["counts"]["cartridges"]
    if loaded.total != declared:
        pytest.skip(
            f"partial checkout: {loaded.total} manifests on disk, catalog declares "
            f"{declared}. Run `git submodule update --init --checkout` over projects/."
        )
    return loaded


@pytest.fixture(scope="module")
def computed(commons):
    return vea.compute(commons)


def _metric(**kwargs):
    base = {"key": "k", "label": "L", "numerator": 1, "denominator": 2}
    base.update(kwargs)
    return vea.Metric(**base)


# ──────────────────────────────────────────────────────────────────────────────
# the guard that makes every other number trustworthy
# ──────────────────────────────────────────────────────────────────────────────

def test_partial_checkout_is_refused_with_the_fix_in_the_message():
    """An under-counted commons must abort, not print a plausible table.

    This is the submodule-empty trap: 34 cartridges (every dual-engine one among
    them) live in submodules, so an uninitialised `projects/*` loses them from
    every metric while the script still runs to completion.
    """
    short = vea.Commons(slugs=["only-one"], manifests={"only-one": {}})
    with pytest.raises(SystemExit) as excinfo:
        vea.assert_commons_complete(short)
    message = str(excinfo.value)
    assert "git submodule update" in message
    assert "under-count" in message


def test_complete_commons_passes_the_guard(commons):
    vea.assert_commons_complete(commons)


def test_commons_total_matches_the_catalog(commons):
    declared = json.loads(vea.CATALOG_JSON.read_text(encoding="utf-8"))["counts"]["cartridges"]
    assert commons.total == declared


# ──────────────────────────────────────────────────────────────────────────────
# the private cartridges are never measured
# ──────────────────────────────────────────────────────────────────────────────

def test_unpublished_cartridges_are_excluded_from_every_measurement():
    """CI checks out the private submodules, so this filter is load-bearing there.

    The exclusion set is imported from the catalog generator rather than restated,
    so this asserts the two agree instead of asserting a second copy of the list.
    """
    assert vea.CLIENT_PRIVATE, "the catalog generator must define an exclusion set"
    measured = set(vea.load_commons().slugs)
    assert measured.isdisjoint(vea.CLIENT_PRIVATE)


def test_exclusion_set_matches_the_catalog_generator():
    sys.path.insert(0, str(REPO / "scripts" / "qa"))
    import generate_commons_catalog as gen

    assert vea.CLIENT_PRIVATE is gen.CLIENT_PRIVATE


# ──────────────────────────────────────────────────────────────────────────────
# the committed document is the recomputation
# ──────────────────────────────────────────────────────────────────────────────

def test_committed_audit_table_matches_a_fresh_recomputation(computed):
    """What `--check` gates on, asserted in-process."""
    metrics, context = computed
    current = vea.AUDIT_MD.read_text(encoding="utf-8")
    assert current == vea.splice(current, vea.render_markdown(metrics, context)), (
        "docs/strategy/VALUE-EXTRACTION-AUDIT.md has drifted; regenerate with "
        "`python3 scripts/qa/value_extraction_audit.py --write`"
    )


def test_the_2026_08_section_is_preserved_verbatim():
    """The old ratios are evidence. Re-measuring must not rewrite them."""
    doc = vea.AUDIT_MD.read_text(encoding="utf-8")
    assert "## 2026-08-06 — original audit" in doc
    assert "## 2026-09-02 — re-measured" in doc
    # a sample of the 326-era figures that must survive untouched
    for original in ("883 camera_views across 293 manifests",
                     "303/326 manifests carry presets (1,021 total)",
                     "555 bilingual constraints across 287 objects"):
        assert original in doc


def test_every_unmeasurable_claim_is_named_in_the_document():
    doc = vea.AUDIT_MD.read_text(encoding="utf-8")
    assert vea.NOT_RECOMPUTABLE
    for claim, why in vea.NOT_RECOMPUTABLE:
        assert claim in doc, f"undeclared unmeasurable claim: {claim}"
        assert why in doc, f"unexplained unmeasurable claim: {claim}"
        assert len(why) > 40, f"a one-word excuse is not a reason: {claim}"


def test_splice_refuses_a_document_without_markers():
    with pytest.raises(SystemExit):
        vea.splice("# no markers here\n", "block")


def test_splice_replaces_only_the_marked_block():
    doc = f"head\n{vea.TABLE_BEGIN}\nstale\n{vea.TABLE_END}\ntail\n"
    out = vea.splice(doc, f"{vea.TABLE_BEGIN}\nfresh\n{vea.TABLE_END}")
    assert out == f"head\n{vea.TABLE_BEGIN}\nfresh\n{vea.TABLE_END}\ntail\n"


# ──────────────────────────────────────────────────────────────────────────────
# ratio + delta arithmetic
# ──────────────────────────────────────────────────────────────────────────────

def test_share_metrics_render_percentages_and_percentage_points():
    m = _metric(numerator=250, denominator=500, base_numerator=163,
                base_denominator=326)
    assert m.fmt_ratio(m.ratio) == "50.0%"
    assert m.delta == "+0.0 pp"


def test_mean_metrics_render_a_rate_not_a_percentage():
    m = _metric(numerator=1209, denominator=500, unit="mean",
                base_numerator=883, base_denominator=326)
    assert m.fmt_ratio(m.ratio) == "2.42"
    assert m.delta == "-0.29"


def test_a_metric_without_a_baseline_says_new_rather_than_comparing_to_zero():
    m = _metric(numerator=22, denominator=500)
    assert m.base_ratio is None
    assert m.base_cell == "—"
    assert m.delta == "new in 2026-09"


def test_an_approximate_baseline_is_marked_as_approximate():
    m = _metric(numerator=210, denominator=500, base_numerator=98,
                base_denominator=326, approx_base=True)
    assert m.base_cell.startswith("~98 / 326")


def test_every_stated_baseline_is_a_well_formed_ratio(computed):
    metrics, _ = computed
    for m in metrics:
        if m.base_numerator is None:
            assert m.base_denominator is None, f"{m.key} has a denominator with no figure"
            continue
        assert m.base_denominator, f"{m.key} states a baseline with no denominator"
        assert m.base_numerator >= 0, f"{m.key} baseline is negative"
        if m.unit == "pct":
            # a share cannot exceed its denominator; a per-cartridge mean can
            assert m.base_numerator <= m.base_denominator, f"{m.key} baseline > 100%"


def test_metric_keys_are_unique(computed):
    metrics, _ = computed
    keys = [m.key for m in metrics]
    assert len(keys) == len(set(keys))


# ──────────────────────────────────────────────────────────────────────────────
# the individual measurements
# ──────────────────────────────────────────────────────────────────────────────

def test_commons_denominator_is_used_for_cartridge_share_metrics(computed):
    """Every per-cartridge share must be over the whole commons, never a subset."""
    metrics, context = computed
    total = context["commons_total"]
    per_cartridge = {"cadquery_first", "camera_view_coverage", "preset_coverage",
                     "constraint_coverage", "material_awareness", "dual_engine",
                     "cdg_interface_coverage", "wearable_domain", "flange_interface",
                     "verification_block", "commons_licensed"}
    for m in metrics:
        if m.key in per_cartridge:
            assert m.denominator == total, f"{m.key} is not measured over the commons"
            assert m.numerator <= total


def test_dual_engine_agrees_with_the_committed_catalog(computed):
    """The row most likely to read 0 on a partial checkout, cross-checked."""
    metrics, _ = computed
    catalog = json.loads(vea.CATALOG_JSON.read_text(encoding="utf-8"))
    row = next(m for m in metrics if m.key == "dual_engine")
    assert row.numerator == catalog["counts"]["dual_engine"]
    assert row.numerator > 0


def test_cdg_interface_coverage_agrees_with_the_committed_catalog(computed):
    metrics, _ = computed
    catalog = json.loads(vea.CATALOG_JSON.read_text(encoding="utf-8"))
    row = next(m for m in metrics if m.key == "cdg_interface_coverage")
    assert row.numerator == catalog["counts"]["with_cdg_interfaces"]


def test_licence_row_counts_and_does_not_judge(computed):
    """This audit reports licence counts; it never picks or changes one."""
    metrics, context = computed
    catalog = json.loads(vea.CATALOG_JSON.read_text(encoding="utf-8"))
    row = next(m for m in metrics if m.key == "commons_licensed")
    assert row.numerator == catalog["counts"]["with_commons_license"]
    assert sum(context["licences"].values()) == context["commons_total"]


def test_family_taxonomy_comes_from_the_api_not_a_copy():
    keys, normalize_family = vea._family_taxonomy()
    assert len(keys) == len(set(keys)), "taxonomy keys must be de-duplicated"
    assert normalize_family("VESA MIS-D 100 mm") == "vesa"
    # "internal…" is private geometry, never a shared standard — the whole
    # prefixed class is rejected, and the audit's family coverage depends on it.
    assert normalize_family("internal peg grid 8mm") is None
    assert normalize_family("") is None


def test_family_metrics_are_bounded_by_the_taxonomy(computed):
    metrics, context = computed
    populated = next(m for m in metrics if m.key == "family_taxonomy_populated")
    assert populated.denominator == context["family_taxonomy_keys"]
    assert populated.numerator <= populated.denominator


# ──────────────────────────────────────────────────────────────────────────────
# locale + landing-gallery readers, on inputs the test controls
# ──────────────────────────────────────────────────────────────────────────────

def test_locale_stats_counts_keys_and_untranslated_markers(tmp_path, monkeypatch):
    (tmp_path / "en.json").write_text(
        json.dumps({"a": "One", "nested": {"b": "Two"}}), encoding="utf-8")
    (tmp_path / "de.json").write_text(
        json.dumps({"a": "[UNTRANSLATED] One", "nested": {"b": "Zwei"}}), encoding="utf-8")
    monkeypatch.setattr(vea, "LOCALES_DIR", tmp_path)

    stats = vea.locale_stats()
    assert stats["en"] == {"keys": 2, "untranslated": 0}
    assert stats["de"] == {"keys": 2, "untranslated": 1}


def test_untranslated_marker_is_counted_wherever_it_sits_in_the_string(tmp_path, monkeypatch):
    """`resolveTranslation` returns any truthy value, so a marker anywhere still ships."""
    (tmp_path / "fr.json").write_text(
        json.dumps({"a": "Save [UNTRANSLATED]"}), encoding="utf-8")
    monkeypatch.setattr(vea, "LOCALES_DIR", tmp_path)
    assert vea.locale_stats()["fr"]["untranslated"] == 1


def test_quadrilingual_row_covers_exactly_the_four_partial_locales(computed):
    metrics, context = computed
    row = next(m for m in metrics if m.key == "quadrilingual_coverage")
    expected_keys = sum(context["locales"][lang]["keys"] for lang in vea.QUAD_LOCALES)
    expected_markers = sum(context["locales"][lang]["untranslated"] for lang in vea.QUAD_LOCALES)
    assert row.denominator == expected_keys
    assert row.numerator == expected_keys - expected_markers
    assert "en" not in vea.QUAD_LOCALES and "es" not in vea.QUAD_LOCALES


def test_landing_gallery_slugs_are_read_from_the_generated_array(tmp_path, monkeypatch):
    generated = tmp_path / "projects.ts"
    generated.write_text(
        '// AUTO-GENERATED\nexport const PROJECTS = [\n'
        '  { slug: "alpha", name: "A" },\n'
        '  { slug: "beta", name: "B" },\n];\n',
        encoding="utf-8")
    monkeypatch.setattr(vea, "LANDING_PROJECTS_TS", generated)
    assert vea.landing_gallery_slugs() == {"alpha", "beta"}


def test_landing_gallery_reader_tolerates_a_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(vea, "LANDING_PROJECTS_TS", tmp_path / "absent.ts")
    assert vea.landing_gallery_slugs() == set()


# ──────────────────────────────────────────────────────────────────────────────
# output shapes
# ──────────────────────────────────────────────────────────────────────────────

def test_json_output_is_parseable_and_carries_every_metric(computed):
    metrics, context = computed
    payload = json.loads(vea.to_json(metrics, context, None))
    assert payload["context"]["commons_total"] == context["commons_total"]
    assert len(payload["metrics"]) == len(metrics)
    assert {m["key"] for m in payload["metrics"]} == {m.key for m in metrics}
    assert len(payload["not_recomputable"]) == len(vea.NOT_RECOMPUTABLE)
    assert "cohorts" not in payload


def test_text_table_has_one_row_per_metric(computed):
    metrics, context = computed
    text = vea.render_text(metrics, context)
    for m in metrics:
        assert m.label.replace("`", "") in text


def test_cohort_split_is_optional_and_never_gates_the_check(commons):
    """--check must not need git history: manifest-validation checks out at depth 1."""
    cohorts = vea.cohort_report(commons)
    if cohorts is None:
        pytest.skip(f"{vea.AUDIT_COMMIT} unreachable — shallow clone, as in CI")
    assert cohorts["audit_era"]["cartridges"] + cohorts["added_since"]["cartridges"] == (
        commons.total
    )
    # The audit-era cohort recomputed today must still reproduce the published
    # 2026-08 figures; if it stops doing so, the extraction logic has drifted
    # away from the one that produced them.
    era = cohorts["audit_era"]["metrics"]
    assert era["cadquery_first"]["numerator"] == 300
    assert era["constraint_coverage"]["numerator"] == 287
    assert era["material_awareness"]["numerator"] == 310
    assert era["tolerance_by_material"]["numerator"] == 294
    assert era["shrinkage_compensation"]["numerator"] == 30
    assert era["recycled_material_toggle"]["numerator"] == 16
