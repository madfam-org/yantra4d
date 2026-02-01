# Qubic Platform Roadmap

Strategic features for future implementation, documented for planning and prioritization.

---

## 3.1 — Product Configurator Storefront Mode

**Goal**: Turn Qubic into a micro-SaaS for 3D-printed product businesses.

**Combines existing features**:
- `access_control` (manifest schema already supports tiers: public/free/pro/admin)
- Shareable URLs (`useShareableUrl.js` — base64url param encoding)
- BOM with supplier links
- Materials and print estimation
- Assembly steps

**New work required**:
- "Customer view" layout that hides developer UI (parameter groups, SCAD info)
- Datasheet PDF generation from manifest + rendered STL thumbnail
- Storefront landing page per project (public URL, product description, preset gallery)
- Optional Stripe/payment integration for premium configurations

**Why it matters**: A user configures a motor mount, sees the NEMA 17 in preview, gets a build guide PDF with purchase links, and shares a URL. That workflow doesn't exist in any web-based parametric tool today.

---

## 3.2 — BOSL2 Attachment-Aware Auto-Assembly

**Goal**: Automatically generate `assembly_steps` from BOSL2 `attach()` / `position()` calls in SCAD source.

**Implementation path**:
1. Extend `scad_analyzer.py` to parse `attach()`, `position()`, and `orient()` calls
2. Build a dependency graph of part-to-part connections
3. Topological sort → ordered assembly sequence
4. Infer camera positions from attachment coordinates
5. Write generated `assembly_steps` into project manifest

**Why it matters**: Manual assembly authoring is the highest-friction part of creating a complete manifest. Auto-generation from BOSL2 attachment semantics removes that barrier for library-aware projects.

---

## 3.3 — NopSCADlib Component Catalog Widget

**Goal**: Visual hardware selector that auto-adjusts parametric geometry.

**Manifest declaration**:
```json
{
  "widget": {
    "type": "component-picker",
    "catalog": "nopscadlib/bearings"
  }
}
```

**Implementation path**:
1. Parse NopSCADlib catalog metadata (dimensions, specs, supplier URLs)
2. New widget type in Controls.jsx: visual grid of hardware components
3. Selection updates dependent parameters (bore diameter, mounting holes, etc.)
4. Preview shows selected component via `static_stl` reference geometry

**Why it matters**: Bridges the gap between parametric design and real hardware selection. Users pick a bearing from a visual catalog and the mount auto-adjusts.

---

## 3.4 — MCAD to BOSL2 Gear Migration

**Goal**: Replace MCAD `involute_gears` with BOSL2 `gears.scad` across existing projects.

**BOSL2 advantages over MCAD**:
- Bevel gears, worm gears, rack-and-pinion (MCAD only has spur/involute)
- `spur_gear()` with built-in shaft bore, pressure angle, helical angle
- `gear_dist()` for accurate center distance calculation
- Active maintenance (MCAD is effectively unmaintained)

**Migration steps**:
1. Identify all projects using `use <MCAD/involute_gears.scad>`
2. Map MCAD API calls to BOSL2 equivalents
3. Update SCAD files and verify geometry output matches
4. Update manifests if parameter names change

**Risk**: Low — BOSL2 is already a submodule in `libs/`. The gear-reducer project (Tier 1) already demonstrates the BOSL2 gear API.

---

## Priority Matrix

| Feature | Impact | Effort | Dependencies |
|---------|--------|--------|--------------|
| Storefront Mode | High | Large | access_control, PDF gen |
| Auto-Assembly | Medium | Medium | scad_analyzer extension |
| Component Catalog | Medium | Medium | NopSCADlib metadata parser |
| MCAD→BOSL2 Gears | Low | Small | None (BOSL2 already available) |
