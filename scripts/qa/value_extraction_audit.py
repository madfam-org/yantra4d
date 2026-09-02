#!/usr/bin/env python3
"""Re-measure the Value-Extraction Audit against the commons that exists today.

`docs/strategy/VALUE-EXTRACTION-AUDIT.md` was written on 2026-08-06 (commit
f2cff0d7) over a commons of 326 project directories, and every finding it ranks
carries a ratio over that 326. The commons is now 500 published cartridges, so
each of those ratios is a claim about a repo that no longer exists. This script
recomputes them from the manifests and `docs/commons-catalog.json` on disk, so
the audit's numbers are a measurement anyone can repeat rather than a snapshot
that quietly rots.

What it measures, and what it refuses to measure
------------------------------------------------
Every row below is derived mechanically from `projects/*/project.json`, the
generated commons catalog, the studio locale files, or the CDG family taxonomy
in `apps/api`. Several figures the 2026-08 audit cites are *not* measurements —
they are an auditor's judgement (effort/ROI ratings, the CONFIRMED/PARTIAL/
REFUTED split), a claim about frontend code reachability, or the output of a
different QA lane. Those are listed by `NOT_RECOMPUTABLE` and printed under the
table instead of being approximated with a proxy: a wrong number that looks
computed is worse than an honest gap.

The submodule-empty trap
------------------------
34 of the 500 cartridges live in submodules, and every dual-engine cartridge is
one of them. With `projects/*` uninitialised the manifests simply are not there,
each metric silently loses those cartridges, and the table still prints. So the
on-disk cartridge count is asserted against `counts.cartridges` in the committed
catalog before any number is trusted; a mismatch is a hard failure with the
`git submodule update` line needed to fix it.

Usage:
    python3 scripts/qa/value_extraction_audit.py            # print the table
    python3 scripts/qa/value_extraction_audit.py --json     # machine-readable
    python3 scripts/qa/value_extraction_audit.py --cohorts  # audit-era vs since
    python3 scripts/qa/value_extraction_audit.py --write    # refresh the doc table
    python3 scripts/qa/value_extraction_audit.py --check    # CI drift gate
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import re
import subprocess
import sys
import textwrap
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROJECTS = REPO / "projects"
CATALOG_JSON = REPO / "docs" / "commons-catalog.json"
AUDIT_MD = REPO / "docs" / "strategy" / "VALUE-EXTRACTION-AUDIT.md"
LOCALES_DIR = REPO / "apps" / "studio" / "src" / "locales"
LANDING_PROJECTS_TS = REPO / "apps" / "landing" / "src" / "data" / "projects.ts"

TABLE_BEGIN = "<!-- BEGIN VALUE_EXTRACTION_TABLE -->"
TABLE_END = "<!-- END VALUE_EXTRACTION_TABLE -->"

# The commit that shipped the 2026-08 audit. Used only by --cohorts, to split
# today's commons into "was already here when the audit ran" and "arrived since".
AUDIT_COMMIT = "f2cff0d7"
AUDIT_DATE = "2026-08-06"
BASE_DENOM = 326  # every project directory at AUDIT_COMMIT, non-Commons ones included

# The four locales the audit calls "half-empty". en/es are the authored pair.
QUAD_LOCALES = ("de", "fr", "pt", "zh")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_commons_catalog import (
    CLIENT_PRIVATE,
    _engine_support,
)


def _family_taxonomy():
    """The real CDG family taxonomy from the API, not a copy of it.

    `normalize_family` is the function the compatibility graph and the standards
    browser both resolve through; re-implementing it here would let the audit
    and the product disagree about what a family is. The import pulls in
    `apps/api/config.py`, which logs a warning about unset AI keys — silenced so
    `--json` stays parseable.
    """
    sys.path.insert(0, str(REPO / "apps" / "api"))
    logging.disable(logging.WARNING)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            from services.core.compatibility_graph import (
                _FAMILY_PATTERNS,
                normalize_family,
            )
    finally:
        logging.disable(logging.NOTSET)
    return sorted({fam for _, fam in _FAMILY_PATTERNS}), normalize_family


# ── metrics that are judgement, code-reachability, or another lane's output ────
# Each entry: (what the audit claims, why this script will not put a number on it).
NOT_RECOMPUTABLE: list[tuple[str, str]] = [
    (
        "40 findings — 12 CONFIRMED, 28 PARTIAL, 2 REFUTED",
        ("an auditor's classification of evidence strength, not a property of the "
        "commons; nothing on disk decides whether a finding is PARTIAL."),
    ),
    (
        "Effort (S / S–M / M) and ROI (exceptional / high / medium) per row",
        ("estimates. Recomputing them would mean inventing a cost model the audit "
        "never had."),
    ),
    (
        "#11 '~94% of constraints are effectively unexercised in discovery/UX'",
        ("a claim about how far a UI surfaces data, with no mechanical definition of "
        "'exercised'. Measurable only by instrumenting the product."),
    ),
    (
        ("#3 'PrintPanel.tsx 0 importers', #3b 'AnimationPanel unmounted', "
        "#9 'graph endpoint, 0 UI refs'"),
        ("frontend import-graph reachability. Real, but it is a TypeScript module "
        "question, not a manifest ratio; the studio's own lint/test lanes own it."),
    ),
    (
        "#6 'i18n_audit.py reports 47 strings'",
        ("the hardcoded-string heuristic belongs to scripts/qa/i18n_audit.py and is "
        "ratcheted against its own baseline. Duplicating the scan here would give "
        "the repo two disagreeing counts. Locale key parity and [UNTRANSLATED] "
        "markers ARE in the table — those are data, not a heuristic."),
    ),
    (
        ("#1 'reportlab absent from requirements.txt', #12 'no test references "
        "simulate_bp', #13 'tsc --noEmit exits 2'"),
        ("states of the code, resolved or not by a commit rather than by the "
        "commons growing. Running them is what CI's backend/studio lanes do."),
    ),
    (
        "Verification totals: 'backend 29 tests', 'frontend 1548 tests'",
        ("require executing both suites. CI reports them per run; a number frozen "
        "into a document is stale the next merge."),
    ),
]


@dataclass
class Metric:
    key: str
    label: str
    numerator: int
    denominator: int
    unit: str = "pct"          # "pct" → share of the commons; "mean" → per cartridge
    base_numerator: int | None = None   # the 2026-08 figure, over BASE_DENOM
    base_denominator: int | None = None
    approx_base: bool = False   # the audit stated the baseline with a "~"
    note: str = ""

    @property
    def ratio(self) -> float:
        return self.numerator / self.denominator if self.denominator else 0.0

    @property
    def base_ratio(self) -> float | None:
        if self.base_numerator is None or not self.base_denominator:
            return None
        return self.base_numerator / self.base_denominator

    def fmt_ratio(self, value: float | None) -> str:
        if value is None:
            return "—"
        return f"{value * 100:.1f}%" if self.unit == "pct" else f"{value:.2f}"

    @property
    def delta(self) -> str:
        base = self.base_ratio
        if base is None:
            return "new in 2026-09"
        diff = self.ratio - base
        if self.unit == "pct":
            return f"{diff * 100:+.1f} pp"
        return f"{diff:+.2f}"

    @property
    def base_cell(self) -> str:
        if self.base_numerator is None:
            return "—"
        tilde = "~" if self.approx_base else ""
        return (f"{tilde}{self.base_numerator} / {self.base_denominator} = "
                f"{self.fmt_ratio(self.base_ratio)}")


@dataclass
class Commons:
    """Every manifest in the published commons, parsed once."""
    slugs: list[str] = field(default_factory=list)
    manifests: dict[str, dict] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.slugs)


def load_commons(only: set[str] | None = None) -> Commons:
    """Parse every published cartridge manifest.

    `CLIENT_PRIVATE` is imported from the catalog generator rather than restated:
    the two must exclude exactly the same slugs or this audit would report over a
    different commons than the one the catalog publishes. CI checks out the
    private submodules, so the filter is load-bearing there, not decorative.
    """
    commons = Commons()
    for manifest_path in sorted(PROJECTS.glob("*/project.json")):
        slug = manifest_path.parent.name
        if slug in CLIENT_PRIVATE:
            continue
        if only is not None and slug not in only:
            continue
        commons.slugs.append(slug)
        commons.manifests[slug] = json.loads(manifest_path.read_text(encoding="utf-8"))
    return commons


def assert_commons_complete(commons: Commons) -> None:
    """Refuse to report numbers over a partially checked-out commons."""
    if not CATALOG_JSON.exists():
        raise SystemExit(f"ERROR: {CATALOG_JSON.relative_to(REPO)} is missing")
    expected = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))["counts"]["cartridges"]
    if commons.total != expected:
        raise SystemExit(
            f"ERROR: found {commons.total} cartridge manifest(s) on disk but "
            f"docs/commons-catalog.json declares {expected}.\n"
            "Every metric below would silently under-count. Initialise the "
            "project submodules first:\n"
            "  git submodule update --init projects/\n"
            "(no --checkout: `update = none` keeps the two private submodules empty, "
            "and --checkout would override it)."
        )


def _hyper(manifest: dict) -> dict:
    """The hyperobject block, wherever this manifest generation put it."""
    top = manifest.get("hyperobject")
    if isinstance(top, dict) and top:
        return top
    nested = (manifest.get("project") or {}).get("hyperobject")
    return nested if isinstance(nested, dict) else {}


def _list_len(manifest: dict, key: str) -> int:
    value = manifest.get(key)
    return len(value) if isinstance(value, (list, dict)) else 0


def _material_flags(manifest: dict) -> list[str]:
    block = _hyper(manifest).get("material_awareness")
    if not isinstance(block, dict):
        return []
    return [flag for flag, value in block.items() if value is True]


def _cdg_interfaces(manifest: dict) -> list[dict]:
    return [i for i in (_hyper(manifest).get("cdg_interfaces") or []) if isinstance(i, dict)]


def landing_gallery_slugs() -> set[str]:
    """Slugs the public landing gallery can show.

    `apps/landing/src/data/projects.ts` is a generated static array the gallery
    filters client-side — audit #8's whole point. It is read as text rather than
    executed: a regex over the generated `slug: "…"` fields is enough, and the
    file's header says it is machine-written, so the shape is stable.
    """
    if not LANDING_PROJECTS_TS.exists():
        return set()
    return set(re.findall(r'slug:\s*"([^"]+)"',
                          LANDING_PROJECTS_TS.read_text(encoding="utf-8")))


def has_fc_bridge_section(slug: str) -> bool:
    """Does this cartridge's README name its Fashion Cabinet bridge?

    The wearables campaign (docs/strategy/WEARABLES-COVERAGE.md, principle 4)
    requires every cartridge on the shelf to end its README with a section
    naming the garments expected to consume it and the params that size the
    mating geometry. That section is the human half of the cross-commons
    contract; the flange interface is the machine half.
    """
    for candidate in (PROJECTS / slug / "docs" / "README.md", PROJECTS / slug / "README.md"):
        try:
            if "Fashion Cabinet bridge" in candidate.read_text(encoding="utf-8"):
                return True
        except OSError:
            continue
    return False


def locale_stats() -> dict:
    """Key parity and [UNTRANSLATED] markers per studio locale.

    The marker is the point: `resolveTranslation` returns the stored string if it
    is truthy, and "[UNTRANSLATED] Save" is truthy, so a marked key renders the
    marker to the user rather than falling back to English.
    """
    stats: dict[str, dict] = {}
    for path in sorted(LOCALES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))

        def walk(node, prefix=""):
            if isinstance(node, dict):
                for k, v in node.items():
                    yield from walk(v, f"{prefix}.{k}" if prefix else k)
            else:
                yield prefix, node

        pairs = list(walk(data))
        stats[path.stem] = {
            "keys": len(pairs),
            "untranslated": sum(
                1 for _, v in pairs if isinstance(v, str) and "[UNTRANSLATED]" in v
            ),
        }
    return stats


def compute(commons: Commons) -> tuple[list[Metric], dict]:
    """Every recomputable ratio the 2026-08 audit defines, plus the 2026-09 additions."""
    total = commons.total
    catalog = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))

    cadquery_first = 0
    dual_engine = 0
    camera_manifests = camera_total = 0
    preset_manifests = preset_total = 0
    constraint_manifests = constraint_total = 0
    material_aware = 0
    flags = {"tolerance_by_material": 0, "shrinkage_compensation": 0,
             "recycled_material_toggle": 0}
    animations = 0
    interface_manifests = interface_total = 0
    flange_cartridges = 0
    wearable = 0
    licensed = 0
    step_export = 0
    verification = 0
    fc_bridge_readme = 0

    family_keys, normalize_family = _family_taxonomy()
    families_seen: set[str] = set()
    family_cartridges = 0

    for slug in commons.slugs:
        m = commons.manifests[slug]
        project = m.get("project") or {}
        hyper = _hyper(m)

        if project.get("engine") == "cadquery":
            cadquery_first += 1
        if _engine_support(m, PROJECTS / slug)[1]:
            dual_engine += 1

        if n := _list_len(m, "camera_views"):
            camera_manifests += 1
            camera_total += n
        if n := _list_len(m, "presets"):
            preset_manifests += 1
            preset_total += n
        if n := _list_len(m, "constraints"):
            constraint_manifests += 1
            constraint_total += n

        block = hyper.get("material_awareness")
        if isinstance(block, dict) and block:
            material_aware += 1
        for flag in _material_flags(m):
            if flag in flags:
                flags[flag] += 1

        if m.get("animations"):
            animations += 1
        if m.get("verification"):
            verification += 1

        interfaces = _cdg_interfaces(m)
        if interfaces:
            interface_manifests += 1
            interface_total += len(interfaces)
        if any(i.get("geometry_type") == "flange" for i in interfaces):
            flange_cartridges += 1

        resolved = {
            fam for fam in (normalize_family(i.get("standard") or "") for i in interfaces)
            if fam
        }
        if resolved:
            family_cartridges += 1
            families_seen |= resolved

        if hyper.get("domain") == "wearable":
            wearable += 1
        if has_fc_bridge_section(slug):
            fc_bridge_readme += 1
        if hyper.get("commons_license") or project.get("license") or m.get("license"):
            licensed += 1
        if "step" in (m.get("export_formats") or []):
            step_export += 1

    gallery = landing_gallery_slugs()
    published = set(commons.slugs)
    gallery_published = len(gallery & published)
    gallery_unpublished = len(gallery - published)

    locales = locale_stats()
    quad_keys = sum(locales[lang]["keys"] for lang in QUAD_LOCALES if lang in locales)
    quad_markers = sum(locales[lang]["untranslated"] for lang in QUAD_LOCALES if lang in locales)
    parity_keys = {stat["keys"] for stat in locales.values()}
    locales_at_parity = sum(
        1 for stat in locales.values() if stat["keys"] == max(parity_keys, default=0)
    )

    metrics = [
        # ── ratios the 2026-08 audit states ───────────────────────────────────
        Metric("cadquery_first", "Cartridges declaring `project.engine: cadquery`",
               cadquery_first, total, base_numerator=300, base_denominator=BASE_DENOM,
               note="audit #2 — 'repo is CadQuery-first (300 cartridges engine:cadquery)'"),
        Metric("camera_view_coverage", "Cartridges declaring ≥1 `camera_views` entry",
               camera_manifests, total, base_numerator=293, base_denominator=BASE_DENOM,
               note="audit REFUTED-2 / #10 — '883 camera_views across 293 manifests'"),
        Metric("camera_views_per_cartridge", "Curated camera angles per cartridge",
               camera_total, total, unit="mean", base_numerator=883,
               base_denominator=BASE_DENOM, note="audit REFUTED-2 / #10"),
        Metric("preset_coverage", "Cartridges shipping ≥1 preset",
               preset_manifests, total, base_numerator=303, base_denominator=BASE_DENOM,
               note="audit #7 — '303/326 manifests carry presets (1,021 total)'"),
        Metric("presets_per_cartridge", "Proven configurations (presets) per cartridge",
               preset_total, total, unit="mean", base_numerator=1021,
               base_denominator=BASE_DENOM, note="audit #7"),
        Metric("constraint_coverage", "Cartridges declaring ≥1 constraint",
               constraint_manifests, total, base_numerator=287,
               base_denominator=BASE_DENOM, note="audit #11 — '287/326 carry constraints'"),
        Metric("constraints_per_cartridge", "Bilingual constraints per cartridge",
               constraint_total, total, unit="mean", base_numerator=555,
               base_denominator=BASE_DENOM, note="audit #11 — '555 bilingual constraints'"),
        Metric("material_awareness", "Cartridges carrying `hyperobject.material_awareness`",
               material_aware, total, base_numerator=310, base_denominator=BASE_DENOM,
               note="audit #4 — '310 objects carry hyperobject.material_awareness'"),
        Metric("tolerance_by_material", "…of which declare `tolerance_by_material`",
               flags["tolerance_by_material"], total, base_numerator=294,
               base_denominator=BASE_DENOM, note="audit SHIPPED #4"),
        Metric("shrinkage_compensation", "…of which declare `shrinkage_compensation`",
               flags["shrinkage_compensation"], total, base_numerator=30,
               base_denominator=BASE_DENOM, note="audit SHIPPED #4"),
        Metric("recycled_material_toggle", "…of which declare `recycled_material_toggle`",
               flags["recycled_material_toggle"], total, base_numerator=16,
               base_denominator=BASE_DENOM, note="audit SHIPPED #4"),
        Metric("animations", "Cartridges declaring an `animations` block",
               animations, total, base_numerator=1, base_denominator=BASE_DENOM,
               note="audit #3b — 'only 1/326 objects even declares animations'"),
        Metric("family_taxonomy_populated", "CDG family keys with ≥1 member in the commons",
               len(families_seen), len(family_keys), base_numerator=55,
               base_denominator=61,
               note="audit #5 — 'a 61-key family taxonomy … 55 families'"),
        Metric("family_coverage", "Cartridges resolving to ≥1 CDG standard family",
               family_cartridges, total, base_numerator=98, base_denominator=BASE_DENOM,
               approx_base=True, note="audit #5 — '55 families cover ~98 objects'"),
        Metric("quadrilingual_coverage",
               f"Studio strings translated across {'/'.join(QUAD_LOCALES)}",
               quad_keys - quad_markers, quad_keys, base_numerator=4 * (327 - 79),
               base_denominator=4 * 327, approx_base=True,
               note="audit #6 — '4 locales ~79 [UNTRANSLATED] markers each', 327 keys × 6"),
        Metric("locale_key_parity", "Studio locale files carrying the full key set",
               locales_at_parity, len(locales), base_numerator=6, base_denominator=6,
               note="audit verification — 'locale parity 327 keys × 6'"),

        # ── measures the 2026-08 audit did not state; added 2026-09 ───────────
        Metric("dual_engine", "Dual-engine cartridges (CadQuery B-Rep + OpenSCAD CSG)",
               dual_engine, total,
               note="catalog `counts.dual_engine`; all of them are submodule-backed"),
        Metric("cdg_interface_coverage", "Cartridges declaring ≥1 CDG interface",
               interface_manifests, total, note="the interoperability surface"),
        Metric("cdg_interfaces_per_cartridge", "Declared CDG interfaces per cartridge",
               interface_total, total, unit="mean"),
        Metric("flange_interface", "Cartridges exposing a `flange` interface",
               flange_cartridges, total,
               note="the FC dimensional handshake — flange only where fabric mates"),
        Metric("wearable_domain", "Cartridges filed `domain: wearable`",
               wearable, total, note="the FC bridge supply side"),
        Metric("fc_bridge_readme", "Cartridges whose README declares a Fashion Cabinet bridge",
               fc_bridge_readme, total,
               note="WEARABLES-COVERAGE principle 4 — the human half of the contract"),
        Metric("landing_gallery_coverage",
               "Cartridges reachable from the public landing gallery",
               gallery_published, total,
               note="audit #8 — the gallery filters a static array, not /api/catalog/search"),
        Metric("landing_gallery_unpublished",
               "Landing-gallery entries the Commons catalog does not publish",
               gallery_unpublished, len(gallery) or 1,
               note="audit #8 — the static array has drifted from the catalog in both "
                    "directions"),
        Metric("step_export", "Cartridges offering STEP (B-Rep) export",
               step_export, total),
        Metric("commons_licensed", "Cartridges carrying an explicit licence",
               licensed, total, note="counts only; licence choice is not this script's call"),
        Metric("verification_block", "Cartridges carrying a `verification` block",
               verification, total, note="the widest remaining gap in the manifest model"),
    ]

    context = {
        "commons_total": total,
        "catalog_declared": catalog["counts"]["cartridges"],
        "audit_commit": AUDIT_COMMIT,
        "audit_date": AUDIT_DATE,
        "base_denominator": BASE_DENOM,
        "locales": locales,
        "family_taxonomy_keys": len(family_keys),
        "licences": _licence_counts(commons),
        "domains": _domain_counts(commons),
    }
    return metrics, context


def _licence_counts(commons: Commons) -> dict[str, int]:
    counts: dict[str, int] = {}
    for slug in commons.slugs:
        m = commons.manifests[slug]
        lic = (_hyper(m).get("commons_license") or (m.get("project") or {}).get("license")
               or m.get("license") or "unlicensed")
        counts[lic] = counts.get(lic, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _domain_counts(commons: Commons) -> dict[str, int]:
    counts: dict[str, int] = {}
    for slug in commons.slugs:
        domain = _hyper(commons.manifests[slug]).get("domain") or "uncategorized"
        counts[domain] = counts.get(domain, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


# ── cohorts: what the audit measured, and what arrived after it ───────────────

def audit_era_slugs() -> set[str] | None:
    """Slugs that existed at AUDIT_COMMIT, or None if history is unavailable.

    `manifest-validation` checks out at depth 1, so the audit commit is usually
    absent in CI. That is why cohorts are a separate, ungated report: --check
    must not depend on git history being present.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "ls-tree", "-r", AUDIT_COMMIT, "--", "projects/"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    slugs = set()
    for line in out.splitlines():
        meta, _, path = line.partition("\t")
        kind = meta.split()[1] if len(meta.split()) > 1 else ""
        parts = path.split("/")
        if len(parts) < 2:
            continue
        if kind == "commit" or (kind == "blob" and parts[-1] == "project.json"):
            slugs.add(parts[1])
    return slugs or None


def cohort_report(commons: Commons) -> dict | None:
    era = audit_era_slugs()
    if era is None:
        return None
    before = load_commons(only={s for s in commons.slugs if s in era})
    after = load_commons(only={s for s in commons.slugs if s not in era})
    return {
        "audit_commit": AUDIT_COMMIT,
        "audit_era": _cohort_stats(before),
        "added_since": _cohort_stats(after),
    }


def _cohort_stats(commons: Commons) -> dict:
    """compute() over a subset. Only the metrics whose denominator IS the subset
    carry over; taxonomy- and locale-denominated rows are repo-wide and would be
    meaningless attributed to one cohort."""
    metrics, _ = compute(commons)
    return {
        "cartridges": commons.total,
        "domains": _domain_counts(commons),
        "metrics": {
            m.key: {"numerator": m.numerator, "denominator": m.denominator}
            for m in metrics if m.denominator == commons.total
        },
    }


# ── rendering ────────────────────────────────────────────────────────────────

def render_text(metrics: list[Metric], context: dict) -> str:
    widths = (60, 9, 11, 9, 22, 16)
    head = ("Metric", "Numerator", "Denominator", "Ratio", f"2026-08 (/{BASE_DENOM})", "Δ")
    lines = [
        f"Yantra4D value-extraction audit — recomputed over {context['commons_total']} cartridges",
        f"(2026-08 baseline: commit {AUDIT_COMMIT}, {AUDIT_DATE}, {BASE_DENOM} project directories)",
        "",
        "  ".join(h.ljust(w) for h, w in zip(head, widths)).rstrip(),
        "  ".join("-" * w for w in widths),
    ]
    for m in metrics:
        label = m.label.replace("`", "")
        cells = (
            label.ljust(widths[0]),
            str(m.numerator).rjust(widths[1]),
            str(m.denominator).rjust(widths[2]),
            m.fmt_ratio(m.ratio).rjust(widths[3]),
            m.base_cell.rjust(widths[4]),
            m.delta.rjust(widths[5]),
        )
        lines.append("  ".join(cells))
    lines += ["", "Not recomputable from the manifests + catalog (judgement, code state,",
              "or another lane's output) — reported, not approximated:"]
    for claim, why in NOT_RECOMPUTABLE:
        lines += textwrap.wrap(claim, 92, initial_indent="  · ", subsequent_indent="    ")
        lines += textwrap.wrap(why, 92, initial_indent="      ", subsequent_indent="      ")
    return "\n".join(lines) + "\n"


def render_markdown(metrics: list[Metric], context: dict) -> str:
    """The block the audit document embeds. `--check` gates on this text."""
    lines = [
        TABLE_BEGIN,
        "",
        ("<!-- Generated by scripts/qa/value_extraction_audit.py — do not edit by hand. "
         "Refresh with `python3 scripts/qa/value_extraction_audit.py --write`. -->"),
        "",
        (f"Recomputed over **{context['commons_total']} cartridges** "
         f"(`docs/commons-catalog.json` `counts.cartridges`). The 2026-08 column is the "
         f"figure the audit published, over the {BASE_DENOM} project directories present at "
         f"`{AUDIT_COMMIT}` ({AUDIT_DATE}) — that denominator counted every directory under "
         f"`projects/`, including the ones the Commons catalog does not publish, so the two "
         f"denominators are not the same set. `~` marks a figure the audit stated "
         f"approximately."),
        "",
        "| Metric | Numerator | Denominator | Ratio | 2026-08 | Δ |",
        "| :-- | --: | --: | --: | --: | --: |",
    ]
    for m in metrics:
        lines.append(
            f"| {m.label} | {m.numerator} | {m.denominator} | {m.fmt_ratio(m.ratio)} | "
            f"{m.base_cell} | {m.delta} |"
        )
    lines += [
        "",
        ("**Not recomputed — reported instead of approximated.** These figures in the "
        "2026-08 section are judgement, frontend code reachability, or another QA lane's "
        "output; a proxy number here would look computed while measuring something else."),
        "",
    ]
    for claim, why in NOT_RECOMPUTABLE:
        lines.append(f"- **{claim}** — {why}")
    lines += ["", TABLE_END]
    return "\n".join(lines)


def to_json(metrics: list[Metric], context: dict, cohorts: dict | None) -> str:
    payload = {
        "context": context,
        "metrics": [
            {**asdict(m), "ratio": m.ratio, "base_ratio": m.base_ratio, "delta": m.delta}
            for m in metrics
        ],
        "not_recomputable": [{"claim": c, "why": w} for c, w in NOT_RECOMPUTABLE],
    }
    if cohorts is not None:
        payload["cohorts"] = cohorts
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def splice(document: str, block: str) -> str:
    if TABLE_BEGIN not in document or TABLE_END not in document:
        raise SystemExit(
            f"ERROR: {AUDIT_MD.relative_to(REPO)} has no {TABLE_BEGIN} … {TABLE_END} markers"
        )
    head, _, rest = document.partition(TABLE_BEGIN)
    _, _, tail = rest.partition(TABLE_END)
    return head + block + tail


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--cohorts", action="store_true",
                    help="also split the commons into audit-era vs added-since "
                         "(needs git history; omitted on a shallow clone)")
    ap.add_argument("--write", action="store_true",
                    help="refresh the generated table in the audit document")
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed audit table has drifted from the "
                         "recomputation")
    args = ap.parse_args()

    commons = load_commons()
    assert_commons_complete(commons)
    metrics, context = compute(commons)

    if args.check:
        current = AUDIT_MD.read_text(encoding="utf-8")
        fresh = splice(current, render_markdown(metrics, context))
        if current != fresh:
            print("ERROR: docs/strategy/VALUE-EXTRACTION-AUDIT.md has drifted from the "
                  "recomputation.")
            print("The commons changed and the audit's numbers no longer describe it.")
            print("Regenerate with: python3 scripts/qa/value_extraction_audit.py --write")
            return 1
        print(f"Value-extraction audit up to date ({context['commons_total']} cartridges, "
              f"{len(metrics)} metrics)")
        return 0

    if args.write:
        current = AUDIT_MD.read_text(encoding="utf-8")
        AUDIT_MD.write_text(splice(current, render_markdown(metrics, context)),
                            encoding="utf-8")
        print(f"Refreshed the generated table in {AUDIT_MD.relative_to(REPO)} "
              f"({context['commons_total']} cartridges)")
        return 0

    cohorts = cohort_report(commons) if args.cohorts else None
    if args.json:
        sys.stdout.write(to_json(metrics, context, cohorts))
        return 0

    sys.stdout.write(render_text(metrics, context))
    if args.cohorts:
        if cohorts is None:
            print("\nCohort split unavailable: commit "
                  f"{AUDIT_COMMIT} is not in this clone's history (shallow checkout).")
        else:
            print()
            for name, label in (("audit_era", f"present at {AUDIT_COMMIT}"),
                                ("added_since", f"added since {AUDIT_DATE}")):
                cohort = cohorts[name]
                print(f"{label}: {cohort['cartridges']} cartridges")
                print("  domains: " + ", ".join(
                    f"{d} {n}" for d, n in cohort["domains"].items()))
                for key in ("cadquery_first", "camera_view_coverage", "preset_coverage",
                            "constraint_coverage", "material_awareness",
                            "recycled_material_toggle", "cdg_interface_coverage",
                            "flange_interface", "wearable_domain"):
                    stat = cohort["metrics"].get(key)
                    if stat:
                        print(f"  {key}: {stat['numerator']} / {stat['denominator']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
