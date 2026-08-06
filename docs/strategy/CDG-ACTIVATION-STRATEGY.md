# Yantra4D — Elevating the Offer: Activating the CDG Moat

**Context:** 300 CadQuery-first hyperobjects, 169 real-world standards, 857 parametric modes, a
scalable discovery layer, and a machine-readable Common Denominator Geometry (CDG) interface model.
**Decision (this session):** the highest-leverage move is to **activate the CDG interoperability
graph** — turn the platform's core thesis from prose into working software — serving **makers /
end-users** first. Below: the state of play, then the top-3 actions ranked by ROI, with the #1 to
build now.

---

## The core insight

Yantra4D's *only* real differentiator versus Thingiverse / Printables / MakerWorld is **CDG: objects
designed to physically interface with one another** via shared standards (NEMA, VESA, DIN-rail,
Gridfinity, 1/4-20, GHT…). Today that thesis is **stated in the README but not activated in the
product.** The proof:

| Signal | Reality today |
|---|---|
| `compatible_with` links in manifests | **22 links across 17 objects** — the graph is ~93% empty |
| Latent compatibility, though | **11 standard-families with ≥3 members already exist** (1/4-20: 10, DIN-rail: 5, PCO 1881: 4, NEMA: 3, GHT: 3, Gridfinity: 3, VESA: 3, ISO-15, M3, M4…) |
| Shared-geometry potential | **96 objects share `socket`, 77 `bolt_pattern`, 46 `snap`, 22 `thread`** — every shared standard is a latent "these snap together" edge |
| Where compatibility surfaces in the UI | **Nowhere.** Not in discovery, not on a project page, not in export. |

**The graph is not missing data — it is missing derivation and surfacing.** Every manifest already
declares `geometry_type` + `standard` + which parameters drive each interface. The edges can be
*computed* from what we already have. This is the cheapest possible path to the platform's most
expensive-sounding promise.

---

## Top 3 actions, ranked by ROI

### ① Compatibility Graph + "Works With" — *the moat, activated* **(BUILD NOW)**

**What:** Derive the interoperability graph from existing CDG metadata and surface it end-to-end for
makers:
1. **Backend derivation** — a `compatibility_graph` service that, for every object, computes its
   edges by matching CDG interfaces on a **normalized standard family** (VESA↔VESA, 1/4-20↔1/4-20,
   Gridfinity-grid↔Gridfinity-grid) and complementary geometry (a `socket` mates a `profile`/`thread`
   of the same standard; a `bolt_pattern` mates a `bolt_pattern`). Emits typed edges
   (`mates_with`, `mounts_to`, `same_family`) with a confidence and the shared standard. Runs over
   the cached catalog index (already built), so it's ~free and self-refreshing.
2. **`GET /api/catalog/graph` + `GET /api/catalog/:slug/works-with`** — the edges as data.
3. **"Works with" on every object** — a section in the Studio browser/project view: *"This Arca
   plate works with 6 things — this clamp, this L-bracket, this tripod head…"* with thumbnails and
   the reason ("shares Arca-Swiss 38 mm dovetail"). One click to the partner object.
4. **Discovery facet upgrade** — the "Connects via / Compatible with" facets we just shipped become
   *navigable relationships*, not just filters: pick a standard → see the whole family that
   interoperates.
5. **Seed the explicit edges** — backfill `compatible_with` in the manifests from the derived
   high-confidence edges (raises 22 → hundreds), so the data is durable, not only computed.

**Why it's #1 (ROI):**
- **Uses assets already built** — the catalog index, the facets, the CDG fields. Net-new surface
  area is small; leverage is enormous.
- **Delivers the maker's actual job-to-be-done** — "find a part that fits the thing I already have."
  No competitor answers this. It converts 300 *isolated* objects into one *composable system*, which
  is a step-change in perceived value with zero new geometry.
- **Compounds** — every new hyperobject authored henceforth auto-joins the graph and makes every
  existing object more valuable (network effect on the catalog itself).
- **De-risks the "300" milestone into a "system" milestone** — the story stops being "we have 300
  parts" (a count anyone can beat) and becomes "we have the only parts that snap together" (a moat).

**Effort:** Medium. Derivation service + 2 endpoints + one Studio UI section + a manifest backfill
script. Days, not weeks. **The single highest ratio of differentiation-gained to effort-spent.**

---

### ② Assembly Composer — *"snap two objects together and export the pair"*

**What:** Let a maker pick two compatible objects (from the graph in ①), auto-mate them on their
shared CDG interface (align the bolt pattern / seat the socket / stack the Gridfinity lip), preview
the combined result, and export the assembly (STEP/3MF with both bodies positioned). Builds directly
on ①'s edges and the existing (scaffolded) `assembly.py` + BOM.

**Why it's #2:** This is the *emotional* payoff of the CDG thesis — not just "these are compatible"
but "here they are, assembled, ready to print." It's the demo that sells the platform. It's #2 not #1
because it **depends on ①** (you can't compose what you haven't computed) and the mating math
(transform resolution per geometry_type) is more involved than derivation. Do it immediately after ①.

**Effort:** Medium-High (per-geometry_type mate transforms, multi-body export, preview). ROI is high
but gated on ①.

---

### ③ Fix the AI Synthesizer to be CDG-native & CadQuery-first — *the self-growing commons*

**What:** The AI synthesizer today emits **OpenSCAD** and is out of step with the 300-object
CadQuery-first commons. Retarget it to: (a) generate CadQuery-first cartridges following the shipped
conventions (the `CARTRIDGE_BRIEF` canon — `PARAM` idiom, watertight techniques, in-enum
geometry_types), and (b) **place new objects into the graph on creation** by asking "what standard
does this interface to?" so every AI-authored object arrives already compatible. Pair with a
one-click "contribute to the commons" flow.

**Why it's #3:** It changes the *growth model* — the commons grows past 300 without us hand-authoring,
and (critically) new objects land **inside** the moat rather than as orphans. It's #3 because it
serves *contributors* more than *makers* (our chosen first audience), and it's only valuable once ①
makes "being in the graph" the thing worth arriving into. High ceiling, later in sequence.

---

## Sequencing

```
NOW  → ① Compatibility Graph + "Works With"   (activate the moat for makers)
NEXT → ② Assembly Composer                     (the payoff demo; needs ①'s edges)
THEN → ③ CDG-native AI Synthesizer             (self-growing commons; lands into ①'s graph)
```

Each stage makes the next cheaper and the whole system more defensible. ① alone re-frames the entire
offering; ② makes it visceral; ③ makes it grow itself. All three convert **existing latent assets**
into offering — the highest-ROI shape of expansion.

## What we are deliberately NOT doing first (and why)
- **Public API/MCP surface** — real long-term moat (matches the ecosystem pattern), but serves
  *developers*, not the maker audience chosen for this push. Strong candidate for the wave after ②.
- **Real physics/FEA simulation** — high cost, GPU infra, and the README is honest that it's
  roadmap/mocked. Not the highest ROI now.
- **Revenue wiring** — the storefront/pricing scaffolds exist; monetization lands better *after* the
  offering is visibly a composable system (① raises willingness-to-pay first).
