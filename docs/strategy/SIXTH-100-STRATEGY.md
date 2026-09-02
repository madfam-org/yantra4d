# Sixth 100 Hyperobjects (#501–600) — Strategy

> **STATUS: PROPOSED, NOT RATIFIED.** RFC 0038 §10.3 ratified the *wave sequencing* —
> waves five through ten, ~100 objects each, selected the way the first hundred was. It
> did not ratify *this list*. The hundred below is a ranked proposal awaiting the same
> evidence pass a Fashion Cabinet band gets before its ranks are claimed. No slug here is
> reserved until the operator rules (§5).

The fifth hundred closed at **500 cartridges** on `feat(commons): the closing six — 500`.
The sixth is the first wave planned against a *measured* interoperability graph rather
than an impression of one: `normalize_family()` and the geometry rules in
`apps/api/services/core/compatibility_graph.py` can be run over `docs/commons-catalog.json`
and will say, per family, exactly who is one member short of a mating pair. That
measurement — not taste — chose the hundred, and it also found six defects in the
measurement itself, reported here rather than quietly routed around.

**Thesis: convert isolates into edges, and pay the four thin domains.** At 500 the commons
resolves 113 standard families and **266 derivable edges**, but **57 families hold exactly
one object**, **70 family-tagged cartridges derive no partner at all**, and — the finding
that reframes the wave — **542 of 942 declared interfaces are `internal`**, invisible to
the graph by construction. Every one-member family is a mating pair that costs one
cartridge. That is the cheapest marginal value on the board, and it is where the sixth
hundred goes.

---

## 1. The census (RFC 0038 §7: census before every slug)

Every figure below was computed from `docs/commons-catalog.json` at 500 cartridges by
re-running `normalize_family()` and the shipped `_COMPLEMENTARY` / `_SELF_MATING` rules.
They are reproducible today, not recalled.

### 1.1 What the 500 cover, per domain

| Domain | At 500 | Share | Read |
| :-- | --: | --: | :-- |
| household | 125 | 25.0% | Deep and broad; the commons' centre of gravity |
| industrial | 108 | 21.6% | Shop, motion, electronics enclosure — the best-linked domain |
| commercial | 75 | 15.0% | Photo/video, RC, automotive clusters |
| wearable | 72 | 14.4% | **Complete per WEARABLES-COVERAGE.md; demand-pulled only** |
| medical | 44 | 8.8% | Lab consumables and assistive; clinic safety now present |
| infrastructure | 33 | 6.6% | Electrical, drainage, signage; thin on HVAC and plumbing |
| hybrid | 14 | 2.8% | Cross-kernel and compliant mechanisms |
| uncategorized | 13 | 2.6% | The pre-taxonomy artistic/legacy set (vases, knots, mazes) |
| soft-robotics | 7 | 1.4% | A real family since new-picks-A, on one shared barb series |
| agriculture | 5 | 1.0% | **Under-served** — graft, hive, milpa, net-cup, dryer |
| consumer | 2 | 0.4% | **Under-served** — molle-pouch, tripod-hub |
| energy | 1 | 0.2% | **Under-served** — mc4-junction alone |
| construction | 1 | 0.2% | **Under-served** — rebar-chair alone |

317 distinct standard strings are referenced and **286 of them are cited by exactly one
cartridge** — the same fact as §1.2, seen from the string side. Breadth is excellent;
depth is what is missing.

### 1.2 Standard families, and who is one member short

Of 942 declared interfaces, 400 carry a non-`internal` standard; those normalize to **113
families across 210 cartridges**, from which **266 edges derive**. Their shape:

| Family size | Count | Meaning |
| --: | --: | :-- |
| ≥4 members | 19 | Working ecosystems |
| exactly 3 | 9 | One member from being ecosystems |
| exactly 2 | 28 | A pair; a third multiplies edges |
| **exactly 1** | **57** | **One member short of a mating pair — the leverage** |

The 19 working ecosystems, with member counts:

`unc-1/4-20` 17 · `pco-1881` 9 · `involute-gear` 7 · `din-rail-35` 7 · `iso-m3` 7 ·
`t-slot-extrusion` 7 · `bearing-608` 6 · `iso-m4` 6 · `gridfinity` 6 · `webbing-strap` 6 ·
`arca-swiss` 5 · `vesa` 5 · `gopro-mount` 4 · `miter-ttrack` 4 · `luer` 4 · `pc-fan` 4 ·
`spi-neck` 4 · `e26-e27-lamp` 4 · `nema-stepper` 4

For each one-member family the census also computes **which geometry a partner must
expose** for an edge to derive: a `pocket` singleton needs a `profile`; a `profile`
singleton needs socket/rail/grid/pocket/snap; a `bolt_pattern` singleton needs another
`bolt_pattern`. That constraint, not intuition, fixed the interface every pick in §3
declares. The 57, with their lone member:

`addressable-led`(matrix-frame) · `ansi-a156-strike`(strike-plate) · `arduino-mount`(devboard-tray) ·
`at-switch-3.5mm`(switch-mount) · `ato-fuse`(obd-holder) · `auto-gauge-52-60`(gauge-pod) ·
`baby-pin-5/8`(spigot-adapter) · `beverage-can`(fridge-dispenser) · `bobbin-class-15`(bobbin-holder) ·
`bottle-cage-boss`(bottle-cage) · `brick-8mm-stud`(brick-tile) · `cable-gland`(cable-gland) ·
`cam-lock`(lock-cam) · `compass-capsule`(compass-housing) · `conduit`(conduit-clip) ·
`crown-cap-26`(bottle-capper) · `cts-pipe`(pipe-clip) · `er-collet`(tool-holder) ·
`ferro-rod`(ferro-handle) · `fpv-cam`(fpv-camera-cage) · `french-cleat`(grid-hub) ·
`hex-bit-1/4`(key-organizer) · `indicator-dovetail`(indicator-base) · `iso-m6`(sentinel-gripper-hyperobject) ·
`iso-m8`(syringe-carriage) · `iso-metric-thread`(fasteners) · `keyhole-hanger`(speaker-bracket) ·
`kurt-vise`(soft-jaw) · `led-strip`(led-channel) · `license-plate`(plate-frame) ·
`mgn-rail`(scara-robotics) · `mic-thread-5/8-27`(mic-clip) · `microswitch-d2f`(endstop-mount) ·
`multiboard`(grid-hub) · `multiconnect`(multiconnect-adapter) · `optic-25.4`(filter-wheel) ·
`paint-pot`(paint-rack) · `paracord-550`(paracord-jig) · `petri-90mm`(petri-rack) ·
`portafilter-58`(coffee-funnel) · `presser-shank`(sewing-guide) · `psu-mount`(psu-mount) ·
`round-duct`(duct-adapter) · `round-rail-25`(rail-mount) · `sae-j1962`(obd-holder) ·
`servo-body`(servo-bracket) · `sma-rf`(fpv-antenna-mount) · `stemfie`(stemfie) ·
`stir-bar`(stirrbar-rack) · `trapezoidal-thread`(leadscrew-nut) · `tubular-drain`(drain-trap) ·
`unc-3/8-16`(camera-quarter-twenty) · `usb-sd-media`(sd-case) · `v-belt`(vbelt-pulley) ·
`wall-box`(outlet-plate) · `watch-lug`(watch-adapter) · `watch-movement`(movement-holder)

### 1.3 The finding that reframes the wave: 57% of the commons' interfaces are invisible

| Measure | Count | Share |
| :-- | --: | --: |
| Declared CDG interfaces across 500 cartridges | 942 | — |
| …whose standard begins `internal` (never normalizes, by design) | **542** | **57.5%** |
| …of which are the bare string `internal` | 520 | 55.2% |
| …of which are *named* internal series | 22 | 2.3% |
| Cartridges whose **every** interface is `internal` | **221** | **44.2%** |
| Cartridges with no `cdg_interfaces` at all | 14 | 2.8% |

`normalize_family()` rejects the whole `internal`-prefixed class deliberately — private
geometry must never masquerade as a shared standard, and that rule is right. But authors
have also used the prefix for genuinely **shared, in-commons** series, and those
relationships are consequently unbuildable and unfindable:

| Named internal series | Cartridges sharing it | What is invisible |
| :-- | --: | :-- |
| `internal (2 / 3 / 4 mm tube ID)` | 5 | The entire soft-robotics barb ecosystem: bellows-actuator, pneu-net-finger, pneumatic-barb-port, suction-cup-bellows, vacuum-manifold-block |
| `internal (19 / 22 / 25 mm ward poles)` + `internal (mates iv-pole-clamp accessory face)` | 2 | The IV-pole clamp ↔ drip-chamber-holder mate, authored on purpose |
| `internal (shared bucket / carboy bore)` | 2 (+`carboy/bucket bore`) | sharps-lid ↔ airlock-grommet |
| `internal (shared leg-tube series, glide variant)` | 2 | walker-glide-cup ↔ mobility-tip |
| `internal (round / D-flat)` | 2 | magnetic-coupling ↔ knob-dshaft |

**A second detail matters as much as the naming.** All five members of the barb series
declare `profile`. Under the shipped rules `profile↔profile` is neither self-mating nor
complementary — so even with a family name, the five would still derive nothing among
themselves. The series is *published* but not *complementary*: it needs an object that
consumes it as a `socket`. Two picks in §3 (#542, #599) do exactly that, which is why they
rank where they do.

**The ask this generates** is in §4.5 and §5: a `commons:<series>` namespace that
normalizes to a family, so a shared in-commons series can be named honestly without
re-opening the door to private geometry.

### 1.4 Six defects in the taxonomy itself

**70 of the 210 family-tagged cartridges derive zero edges.** Most are genuine singletons.
Six are measurement defects, each an edge win with no geometry at all. §7 forbids inflating
a number; it equally forbids quietly benefitting from a wrong one.

| # | Defect | Evidence | Effect |
| --: | :-- | :-- | :-- |
| D1 | `tripod-hub` is orphaned by one punctuation character | It declares `1/4"-20 UNC — major Ø6.35 mm…` and `3/8"-16 UNC — …`; the patterns `1/4[\s-]?20` and `3/8[\s-]?16` allow **one** separator, the strings carry two (`"` then `-`) | The only object declaring both tripod threads joins neither `unc-1/4-20` (17 members) nor `unc-3/8-16`. Its Arca-Swiss interface normalizes fine, which is why the defect is invisible by eye |
| D2 | `seed-tray` derives a **false** edge | Its standard is `1020 tray` — the horticultural 10×20 in propagation tray. The `t-slot-extrusion` pattern lists `1020` (the aluminium profile) as an alternative | A propagation tray is currently reported `same_family` with T-slot extrusion hardware |
| D3 | `19mm` in the `miter-ttrack` pattern captures unrelated hardware | `camlock-latch` (`16/19mm cam-lock`) and `bench-dog` (`19mm/20mm dog hole`) both land in `miter-ttrack` | `camlock-latch` never joins `cam-lock`, where it belongs; two false T-track edges |
| D4 | `iso\s*15` matches any ISO number beginning 15 | `ISO 15488` (ER collets), `ISO 1503`, etc. would be filed as `bearing-608` | Not yet triggered by a live cartridge — it *was* triggered by a draft standard string for #525 during this planning pass. A latent trap, fixed by a word boundary |
| D5 | Three real ecosystems have no pattern at all | `US bar designations #3/#4/#5` (rebar-chair), `Langstroth …` (hive-frame-spacer), `carboy/bucket bore` (airlock-grommet) | The agriculture and construction picks in §3 derive nothing without them |
| D6 | The `internal` prefix has no honest alternative for shared series | §1.3 | 542 interfaces, 221 cartridges, and five real shared series invisible |

**A seventh, adjacent finding: the `difficulty` discovery facet is dead.**
`catalog_index.py:139` reads `proj.get("difficulty", "beginner")` and **0 of 466 local
manifests declare it** — so 100% of the commons filters as "beginner". The T column in §3
is a *build-effort* tier; the wave should also write the manifest facet so the filter stops
lying. Backfilling the existing 500 is out of scope here.

### 1.5 Wearables: the census says the shelf is closed

`WEARABLES-COVERAGE.md` declared all twelve garment-hardware categories complete at waves
U–Z, and the standing ruling made the shelf demand-pulled. The census confirms it from the
consuming side (§2.2): across `fc200`, `fc300`, `fc400` and `fc500`, **281 Fashion Cabinet
hardware claims resolve to a live y4d slug and exactly one does not.** The sixth hundred
therefore adds exactly one wearable.

---

## 2. Demand signals — what can actually be cited

Four kinds of evidence rank this list. Every row in §3 cites at least one.

### 2.1 Catalog facets (measured, this repo)

- Family size and the 57 one-member families (§1.2) — marginal edge value per cartridge.
- The 70 zero-edge cartridges and the 221 all-`internal` ones (§1.3–1.4) — where a partner
  rescues an object that already exists.
- Domain shares (§1.1) — four domains under 1.5% against real-world demand that is not.
- 286 of 317 standard strings cited once — breadth without depth is the shape to correct.

### 2.2 Fashion Cabinet latent demand (cross-commons, cited)

Cross-referencing every `yantra4d/<slug>` hardware claim in
`/home/user/fashion-cabinet/docs/fc{200,300,400,500}/index.json` against the 500-cartridge
catalog returns **exactly one unresolved claim**: `yantra4d/hammer-loop (co-create)`,
claimed by FC-400 **rank 308 `painters-pant`** (family `workwear_uniforms`, tier 2).

Everything else resolves. `fc500-plan.md` states plainly that "FC-500 ships with zero
co-creations — every one of its 84 bridges resolves in the refreshed snapshot".
`fc400-plan.md` names its other seven co-create claims as solids that already exist in the
500 catalog but were not yet in FC's pinned snapshot (`folding-board`, `garment-hanger`,
`shoe-tree`, `garment-clip`, `belt-hanger`), plus the FC-300 carry-over `frog-closure`
(since built, PR #60) and a `side-release-buckle` variant (built). **`hammer-loop` is the
whole of the demand pull, and it is therefore the whole of the wearable allocation.**

### 2.3 External standards with real-world incidence

Where a pick's demand rests on a standard being ubiquitous rather than on a catalog
measurement, the row cites the standard **by number**, and the claim is limited to what the
standard *is*. An installed base we have not measured is not asserted, and no adoption
figure appears anywhere in this document. Designations or dimensions that could not be
confirmed against a primary source during this planning pass are marked **(verify)** and
**must** be checked against the issuing body's table before geometry is written — real
industry dimensions are §7 law, and a plausible number is not a dimension. De-facto
ecosystems with no issuing body (Gridfinity, Multiboard, STEMFIE, Anderson Powerpole,
skate truck patterns, System 32) are labelled de-facto rather than dressed as standards.

### 2.4 Adjacent-repo signals

- `docs/strategy/VALUE-EXTRACTION-AUDIT.md` #5: the family taxonomy and a
  `/api/catalog/families` endpoint already ship with no directory UI — the families this
  wave thickens are queryable the day the cartridges land.
- `docs/cartridges/hyperobject_candidates.md` is a **roadmap brief, not demand** — its own
  banner says the physics pipeline never executes the generated script. It is **not** cited
  as demand for any pick.
- There is **no usage or telemetry data** for the commons anywhere in `docs/audits/*`; the
  audits there are browser, CI and codebase audits. See §6.

---

## 3. The ranked hundred (#501–600)

**Reading the tables.** *P* is the **measured** number of live cartridges the object
derives an edge with, computed by running the shipped rules over the proposed interfaces —
not an estimate. A **°** means that count depends on a §4.5 taxonomy fix landing. A family
in **bold** is closed (1 → 2) by that row. *Eng* is `cq` (CadQuery, the default) or `scad`
(OpenSCAD, used only where the object is a dense repetitive CSG array with no B-Rep
filleting — the case where the Manifold backend is measurably the right kernel per the
AGENTS.md CGAL-vs-Manifold note). *T* is build-effort tier: **T1** prism/revolve, few
booleans · **T2** multi-mode, threads/lofts, parameter families · **T3** thin-wall or
compound geometry where the extremes sweep is expected to bite · **T4** flagship.

All 100 slugs were census-checked against the 500 live slugs: **zero collisions.** Eleven
are deliberate *siblings* of an existing cartridge and are named as such in §3.11.

**One honesty note on P.** Some counts include `iso-m3` / `iso-m4` / `iso-m5` edges — a
partner found because both objects use the same screw size. Those are weak edges and are
marked *(fastener-size)* where they dominate a row. They are reported rather than filtered
because filtering them silently would be the same sin as inflating them.

### 3.1 Household — 22 (#501–522)

| # | Slug | What | Standard(s) | CDG → mates | P | Demand | Eng | T |
| --: | :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| 501 | `led-channel-corner` | 90°/135° corner joiner and end cap for aluminium LED channel | 5050 / 2835 LED strip; 12 & 17 mm channel section **(verify)** | socket → **`led-strip`**: led-channel | 1 | Closes a singleton; corners are the one part every strip run needs and no vendor sells generically | cq | T2 |
| 502 | `multiboard-hook-set` | Snap tiles, hooks and threaded posts for the Multiboard wall grid | Multiboard 25 mm module (de-facto) | grid, snap → **`multiboard`**: grid-hub | 1 | Closes a singleton in a live open wall-system ecosystem the commons already speaks | cq | T2 |
| 503 | `french-cleat-keyhole-plate` | Cleat-hung utility plate presenting keyhole slots on its face | 45° French cleat; keyhole slot for a #8 pan head (6.4 / 11 mm) | rail → **`french-cleat`**: grid-hub; bolt_pattern → **`keyhole-hanger`**: speaker-bracket | 2 | **Closes two singletons with one T1 cartridge** — the best edge-per-effort ratio in the wave | cq | T1 |
| 504 | `pegboard-bin` | Hook-back parts bin for 1 in pegboard | 1 in / 6.35 mm pegboard pitch | snap, grid → `pegboard-1in`: grid-hub, pegboard-hooks | 2 | Thickens a pair; the commons has pegboard hooks and no pegboard storage | cq | T1 |
| 505 | `gu10-track-adapter` | GU10 / B22d lamp head carrier into an E26/E27 socket | IEC 60061-1 GU10, B22d, E26/E27 (7 TPI) | snap → `gu10-lamp`; thread → `e26-e27-lamp`: lamp-adapter-kit, lamp-socket-extender, socket-adapter | 3 | Joins a 2-member family to a 4-member one; lamp retrofit is the commons' most-worked household thread | cq | T2 |
| 506 | `ws2812-diffuser-grid` | Cell-wall diffuser / light-guide grid for addressable matrices | WS2812B / SK6812 ~10 mm pixel pitch | grid → **`addressable-led`**: matrix-frame | 1 | Closes a singleton; a bare matrix without a diffuser is not a display | scad | T2 |
| 507 | `paint-pot-carrier` | Carry tray for hobby paint pots and dropper bottles | Citadel 33 mm pot / Vallejo 17 mm dropper **(verify)** | grid → **`paint-pot`**: paint-rack | 1 | Closes a singleton; paint-rack stores, nothing transports | cq | T1 |
| 508 | `portafilter-cradle` | Tamping cradle and knock seat for espresso baskets | 58 / 54 / 51 mm portafilter basket | socket → **`portafilter-58`**: coffee-funnel | 1 | Closes a singleton; the dosing funnel exists, the tamping station does not | cq | T1 |
| 509 | `bit-holder-block` | Driver-bit block, indexed, Gridfinity-footed | ISO 1173 form C 6.3 (1/4 in hex, 6.35 mm A/F); Gridfinity 42 mm | socket → **`hex-bit-1/4`**: key-organizer; grid → `gridfinity` (5) | 6 | Closes a singleton *and* lands inside the 6-member Gridfinity ecosystem | cq | T1 |
| 510 | `vacuum-hose-cuff` | Domestic and shop vacuum hose-to-tool cuff and reducer series | 32 & 35 mm domestic hose; 2-1/4 & 2-1/2 in shop-vac **(verify)** | socket, profile → *(opens a new family)* | 0 | Dust extraction is the workshop gap the commons never closed; opens the hose-cuff family the next wave thickens | cq | T2 |
| 511 | `tubular-drain-adapter` | Slip-joint tailpiece adapter and reducer | US tubular 1-1/4 / 1-1/2 in slip | socket → **`tubular-drain`**: drain-trap | 1 | Closes a singleton; the trap exists with nothing to join it to | cq | T2 |
| 512 | `spice-shaker-insert` | Dosing, shaker and sift insert for spice jar finishes | GPI 43-485 & 53-485 shaker CT finish **(verify)**; SPI 28-410 | thread → `spi-neck`: growler-cap, pump-adapter, sharps-lid-adapter, squeeze-nozzle | 4 | Thickens a 4-member neck-finish family; refill-not-replace is the household thesis | cq | T1 |
| 513 | `mason-jar-pour-lid` | Pour, strain and sprout lid for mason CT finishes | GPI 70-450 / 86-450 mason CT finish | thread; socket → `bucket-bore`°: airlock-grommet, sharps-lid | 2° | Extends the live mason-finish pair; the sprouting mode also serves the agriculture lane | cq | T2 |
| 514 | `broom-clip-rail` | Spring-clip tool rail for round handle stock | 19–32 mm round handle stock series | snap; rail → `french-cleat`: grid-hub | 1 | Household storage is the deepest domain and still has no handle-capture rail | cq | T1 |
| 515 | `door-strike-guard` | Latch and deadbolt strike reinforcement wrap | ANSI/BHMA A156.2; 1 in bore, 2-3/8 in backset | bolt_pattern, socket → **`ansi-a156-strike`**: strike-plate | 1 | Closes a singleton; strike reinforcement is a named A156.2 failure mode | cq | T2 |
| 516 | `cabinet-cam-escutcheon` | Trim ring and strike for furniture cam locks | Slotted cam-lock tailpiece; 16 / 19 mm furniture cam | socket → **`cam-lock`**: lock-cam, camlock-latch° | 2° | Closes a singleton and — once D3 is fixed — reunites the two cam-lock objects the taxonomy separated | cq | T1 |
| 517 | `curtain-rod-splice` | Inline splice, end stop and finial for curtain rods | 16 / 19 / 25 / 28 mm rod series **(verify)** | socket → *(opens a new family; `curtain-bracket` is all-`internal`)* | 0 | Long-span rods have no printable joint; also the first honest standard on the curtain cluster | cq | T1 |
| 518 | `shelf-pin-jig` | 32 mm line-boring shelf-pin drilling jig | System 32 (de-facto: 32 mm pitch, 5 mm pin, 37 mm setback) | grid, socket → *(opens a new family; `shelf-bracket` is all-`internal`)* | 0 | A real cabinetmaking module the commons references nowhere; opens the family later shelf hardware joins | cq | T2 |
| 519 | `bucket-lid-adapter` | Pail-mouth lid carrying a bottle finish and a grommet boss | Nominal 5 gal / 20 L pail mouth **(verify)**; PCO 1881 | thread → `pco-1881` (9); socket → `bucket-bore`°: airlock-grommet, sharps-lid | **11°** | **Highest measured P in the wave** — joins the bucket-bore cluster to the 9-member PCO 1881 family. Sibling of `sharps-lid-adapter`, not a duplicate (§3.11) | cq | T2 |
| 520 | `dishwasher-tine-cap` | Replacement tine tip caps for dish racks | 2.5–4.0 mm tine wire; food-contact wall floor per the house material-class rule | socket → *(none)* | 0 | **Ranked on demand alone, and flagged as such (§5.4):** a high-value repair part with zero graph leverage | cq | T1 |
| 521 | `roller-blind-end-plug` | Roller-blind tube end plug, idler and chain gear | 25 / 38 mm blind tube; #10 bead chain, 4.5 mm ball / 6 mm pitch **(verify)** | socket → *(opens a new family)* | 0 | Window-covering repair is unrepresented; pairs physically with #517 inside the wave | cq | T2 |
| 522 | `window-screen-corner` | Corner key and spline-groove profile for roll-formed screen frame | 3/4 × 5/16 in US roll-formed screen frame **(verify)** | profile, socket → *(opens a new family)* | 0 | Seasonal repair on a genuine extruded section no commons object addresses | cq | T1 |

### 3.2 Industrial — 20 (#523–542)

| # | Slug | What | Standard(s) | CDG → mates | P | Demand | Eng | T |
| --: | :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| 523 | `robot-tool-flange` | Tool-side adapter plate for a robot wrist flange | **ISO 9409-1**-50-4-M6 (also -31.5-4-M5, -80-6-M6) | bolt_pattern → **`iso-m6`**: sentinel-gripper-hyperobject | 1 | Closes a singleton, and is the only object that would let the soft-robotics grippers mount to anything industrial | cq | T2 |
| 524 | `mgn-carriage-plate` | Riser and tool plate for MGN miniature linear carriages | MGN9 / MGN12 / MGN15 carriage pattern (MGN12H 20×20 M3) **(verify)** | socket → **`mgn-rail`**: scara-robotics; bolt_pattern → `iso-m3` (5, *fastener-size*) | 6 | Closes a singleton; MGN is the default motion rail of the desktop-CNC era | cq | T2 |
| 525 | `er-collet-tray` | ER collet and nut storage, Gridfinity-footed | **DIN 6499** ER11/16/20/25/32; Gridfinity 42 mm | socket → **`er-collet`**: tool-holder; grid → `gridfinity` (5) | 6 | Closes a singleton and joins the Gridfinity ecosystem. *Its draft string `ISO 15488` triggered defect D4 — dropped, and the pattern fixed* | cq | T1 |
| 526 | `vise-jaw-stop` | Workstop and jaw riser for a machine vise | Kurt-style 6 in vise jaw bolt pattern **(verify)** | bolt_pattern → **`kurt-vise`**: soft-jaw | 1 | Closes a singleton; soft-jaw has no partner today | cq | T1 |
| 527 | `servo-linkage-arm` | Servo horn linkage and pushrod arm | 24T Futaba & 25T Spektrum spline; SG90 / MG996R body | bolt_pattern → **`servo-body`**: servo-bracket; spline → `servo-spline` | 1 | Closes a singleton and thickens a pair; linkage is the commonest servo accessory | cq | T2 |
| 528 | `microswitch-guard` | Lever guard and cover for miniature snap switches | Omron D2F (2 × Ø2.0 at 9.5 mm), SS-5GL **(verify)** | bolt_pattern → **`microswitch-d2f`**: endstop-mount | 1 | Closes a singleton and rescues `endstop-mount` from the zero-edge list | cq | T1 |
| 529 | `uno-shield-blank` | Shield and standoff blank on the Arduino Uno–Mega hole pattern | Arduino Uno R3 hole pattern; 2.54 mm header pitch | bolt_pattern → **`arduino-mount`**: devboard-tray; grid → `optical-breadboard`: breadboard-holder, circuit-trainer | 3 | Closes a singleton; the commons trays a board it cannot mount to | cq | T1 |
| 530 | `psu-terminal-shield` | Finger-safe terminal shroud for open-frame PSUs | Meanwell LRS / RS case pattern **(verify)**; IEC 60529 IP2X | bolt_pattern → **`psu-mount`**: psu-mount | 1 | Closes a singleton with a genuine safety function — mains terminals exposed by design | cq | T1 |
| 531 | `tr-nut-flange-block` | Flange-nut housing for trapezoidal leadscrews | **ISO 2904** Tr8×8(P2), Tr10, Tr12; ISO 261 M5 | thread → **`trapezoidal-thread`**: leadscrew-nut; bolt_pattern → `iso-m5` (*fastener-size*) | 2 | Closes a singleton; the anti-backlash nut has nothing to bolt into | cq | T2 |
| 532 | `v-belt-idler-arm` | Tensioner arm carrying a 608 idler for V-belt drives | **ISO 4183** A / SPZ; ISO 15 608 bearing | profile → **`v-belt`**: vbelt-pulley; socket → `bearing-608` (6) | 6 | Closes a singleton and lands in a 6-member bearing family | cq | T2 |
| 533 | `rod-cross-clamp` | Right-angle boss head for lab and optical rod | Ø12 mm / 1/2 in support rod; Ø12.7 mm optical post | socket → `support-rod-12`: flask-clamp, optical-post | 2 | Thickens a pair spanning lab and optics — one clamp serves both benches | cq | T2 |
| 534 | `d-shaft-sleeve` | Adapter sleeve series between round, D-flat, hex and splined shafts | DIN 5480 spline / D-flat; 3–12 mm shaft series | socket, spline → `shaft-spline`: knob-dshaft, spline-hub | 2 | Six shaft-consuming cartridges exist and nothing adapts between shaft forms — the highest physical fan-out in the lane, understated by P | cq | T2 |
| 535 | `zip-tie-mount-base` | Screw-down and adhesive cable-tie base | IEC/EN 62275 cable ties; 2.5 / 3.6 / 4.8 / 7.6 / 9.0 mm widths; ISO 261 M4 fixing | profile; bolt_pattern → `iso-m4` (5, *fastener-size*) | 5 | Cable routing is a five-object cluster (cable-management, strain-relief, drag-chain, cable-wrap, cord-guard) with no anchor | cq | T1 |
| 536 | `din-rail-end-stop` | End bracket, spacer and blanking module for TS35 | **DIN EN 60715** TS35 (35×7.5 and 35×15) | rail → `din-rail-35` (7) | 7 | **Seven existing members mate one rail interface** — the largest genuine-standard edge yield in the wave | cq | T1 |
| 537 | `pi-din-carrier` | SBC carrier clipping a Pi-format board onto TS35 | RPi HAT 58×49 mm, M2.5; DIN EN 60715 TS35 | bolt_pattern → `rpi-mount`: pi-hat-case, sbc-case; rail → `din-rail-35` (7) | **9** | Bridges a 2-member family into a 7-member one; industrial SBC deployment is standard-shaped, not bespoke | cq | T2 |
| 538 | `indicator-dovetail-clamp` | Adapter between a lever-indicator dovetail and an 8 mm stem | 60° lever-indicator dovetail; 8 mm AGD Group 2 stem | socket → **`indicator-dovetail`**: indicator-base; `indicator-stem-8mm`: indicator-holder | 2 | Closes one singleton, thickens a pair, and connects the metrology cluster | cq | T1 |
| 539 | `keyway-hub-blank` | Parallel-key hub and bore blank for printed drive parts | **DIN 6885-1 / ISO 773** parallel keys (Ø8 → 3×3) | socket, spline → `shaft-spline`: knob-dshaft, spline-hub | 2 | Keyed bores are the missing half of every printed pulley in the commons | cq | T2 |
| 540 | `machine-level-pad` | Levelling and anti-vibration foot with a threaded stud | ISO 261 M8 & M10; ISO 261 / ISO 965 thread system | thread → **`iso-m8`**: syringe-carriage; **`iso-metric-thread`**: fasteners | 2 | Closes two singletons and rescues `fasteners` from the zero-edge list; every bench machine needs feet | cq | T1 |
| 541 | `filament-spool-adapter` | Spool hub adapter to a 608 bearing and a variable core | ISO 15 608; 52 / 54 / 56 mm spool core, 32 mm hub **(verify)** | socket → `bearing-608` (6) | 6 | The highest-demand accessory for this commons' own audience, landing in a 6-member family | cq | T1 |
| 542 | `hose-barb-tee` | Tee, elbow and reducer for small-bore tube | **The commons' own 2/3/4 mm barb series**, published by `pneumatic-barb-port`; 4/6 mm push-in per ISO 14743 nominal | socket → `commons-barb-series`°: bellows-actuator, pneu-net-finger, pneumatic-barb-port, suction-cup-bellows, vacuum-manifold-block | 5° | **The object that makes the soft-robotics family real.** All five members publish `profile`; nothing consumes them as a `socket`, so the family cannot mate itself (§1.3). Gated on D6 | cq | T2 |

### 3.3 Commercial — 13 (#543–555)

| # | Slug | What | Standard(s) | CDG → mates | P | Demand | Eng | T |
| --: | :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| 543 | `mic-stand-thread-adapter` | Stand-thread adapter set, 5/8-27 ⇄ 3/8-16 ⇄ 1/4-20 | 5/8"-27 UNS mic thread; 3/8"-16 BSW; ASME B1.1 1/4-20 UNC | thread → **`mic-thread-5/8-27`**: mic-clip; **`unc-3/8-16`**: camera-quarter-twenty; `unc-1/4-20`: ball-socket, gopro-mount, sensor-mount-plate, spigot-adapter, tripod-hub° | **7°** | **Closes two singletons and joins the 17-member largest family** — and its `tripod-hub` edge is the one D1 rescues | cq | T2 |
| 544 | `baby-pin-receiver` | 5/8 in grip baby-pin receiver with a junior adapter | 5/8 in (16 mm) baby pin; 1-1/8 in junior **(verify)** | socket → **`baby-pin-5/8`**: spigot-adapter | 1 | Closes a singleton in the grip and lighting cluster | cq | T1 |
| 545 | `cold-shoe-riser` | Accessory-shoe riser and dual-shoe bar | **ISO 518** accessory shoe | rail → `iso-518-shoe`: shoe-bar, shoe-mount | 2 | Thickens a pair and links it to the rail cluster | cq | T1 |
| 546 | `rail-riser-block` | Riser and adapter across accessory rails | **MIL-STD-1913**; NATO accessory rail; M-LOK | rail → `picatinny`: picatinny-rail, rail-bridge; `nato-rail`: nato-rail | 3 | Both rail families sit at two members sharing one bridge object; the riser is the standard missing part | cq | T1 |
| 547 | `sma-bulkhead-panel` | SMA / RP-SMA bulkhead panel plate | SMA bulkhead nominal Ø6.35 mm; U.FL; ISO 261 M3 | socket → **`sma-rf`**: fpv-antenna-mount; bolt_pattern → `iso-m3` (5, *fastener-size*) | 6 | Closes a singleton; the enclosure family has no RF pass-through | cq | T1 |
| 548 | `fpv-cam-tilt-wedge` | Tilt wedge and mount block for FPV camera bodies | FPV cam widths 14 / 19 / 21 mm (nano / micro / mini) | profile → **`fpv-cam`**: fpv-camera-cage | 1 | Closes a `pocket`-only singleton — the census says a `profile` is exactly what it needs | cq | T1 |
| 549 | `blade-fuse-block` | ATO/Mini blade fuse block with an OBD harness clip | **ISO 8820-3** ATO/Mini; SAE J1962 | profile → **`ato-fuse`** and **`sae-j1962`**: obd-holder | 1 | Closes two singletons that happen to share one lone member — P=1 understates it | cq | T2 |
| 550 | `gauge-panel-blank` | Gauge panel and bezel blank | 52 & 60 mm (2-1/16 & 2-3/8 in) automotive gauge | socket → **`auto-gauge-52-60`**: gauge-pod | 1 | Closes a singleton; the pod exists, the flat-panel case does not | cq | T1 |
| 551 | `bar-end-plug` | Handlebar end plug and expander | ISO handlebar Ø22.2 / 25.4 / 31.8 mm | socket → `handlebar-clamp`: barend-mount, bike-mount | 2 | Thickens a pair; the plug is the part that is always lost | cq | T1 |
| 552 | `frame-boss-adapter` | Bicycle bottle-boss accessory adapter plate | Bicycle water-bottle boss, 64 mm spacing (M5 fixings, deliberately *not* named in the standard string — see §4.6) | bolt_pattern → **`bottle-cage-boss`**: bottle-cage | 1 | Closes a singleton; the boss is the bicycle's universal accessory port | cq | T1 |
| 553 | `compass-baseplate` | Orienteering baseplate with romer scales for a capsule | 20 / 25 mm compass capsule; 1:25 000 & 1:50 000 romer | socket → **`compass-capsule`**: compass-housing | 1 | Closes a singleton; a housed capsule without a baseplate cannot navigate | cq | T1 |
| 554 | `watch-strap-keeper` | Strap keeper and spring-bar fitting jig | 18 / 20 / 22 mm lug; 1.5 & 1.78 mm spring bar **(verify)** | socket → **`watch-lug`**: watch-adapter | 1 | Closes a singleton in the two-object watch cluster | cq | T1 |
| 555 | `round-rail-tee` | Tee, end cap and splice for Ø25 mm round rail | 1 in / 25 mm round rail | socket → **`round-rail-25`**: rail-mount | 1 | Closes a singleton; a rail with no junction is a stick | cq | T1 |

### 3.4 Medical — 9 (#556–564)

| # | Slug | What | Standard(s) | CDG → mates | P | Demand | Eng | T |
| --: | :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| 556 | `at-switch-panel` | Mounting panel and actuation guard for assistive switches | 3.5 mm TS/TRS AT switch jack; ISO 9999 assistive-product classification; ISO 261 M4 | socket → **`at-switch-3.5mm`**: switch-mount; bolt_pattern → `iso-m4` (5, *fastener-size*) | 6 | Closes a singleton in the accessibility cluster, where the mount is the whole barrier to use | cq | T1 |
| 557 | `petri-stack-lid` | Stack lid and incubation tray for 90 mm plates | 90 mm petri body; ANSI/SLAS 1-2004 footprint | grid → **`petri-90mm`**: petri-rack; `slas-microplate`: microplate-tray, pipette-stand, tube-rack | 4 | Closes a singleton and joins a 3-member lab-footprint family | cq | T1 |
| 558 | `conical-tube-opener` | Cap opener and rack insert for conical tubes | 15 / 50 mL conical (Falcon); 17 & 30 mm cap **(verify)** | socket → `conical-tube`: centrifuge-adapter, centrifuge-tube-adapter | 2 | Thickens a pair; doubles as an assistive-grip object for low hand strength | cq | T1 |
| 559 | `slide-staining-rack` | Staining and drying rack for microscope slides | **ISO 8037-1** 25.4 × 76.2 mm | grid, **profile** → `microscope-slide`: microscope-slide-holder, microscope-slide-hyperobject | 2 | Thickens a pair. *The census forced the interface*: both members expose `pocket`, and `pocket↔pocket` does not mate — the rack must present a `profile` | cq | T2 |
| 560 | `optic-lens-tube` | Ø1 in optic lens tube with a retaining ring | Ø25.4 mm optic; SM1 1.035"-40 retaining thread **(verify)** | socket → **`optic-25.4`**: filter-wheel | 1 | Closes a singleton and links the optics cluster to the lab rod family | cq | T2 |
| 561 | `luer-stopcock-body` | Three-way stopcock body and blank | **ISO 80369-7** (6% Luer taper; supersedes ISO 594) | socket, profile → `luer`: dosing-aid, sharps-lid, sharps-lid-adapter, syringe-carriage | 4 | Thickens a 4-member family; the fluidics half of the syringe carriage has no valve | cq | T3 |
| 562 | `iv-pole-tray` | Accessory tray riding the IV-pole dovetail accessory face | 19 / 22 / 25 mm ward pole; the `iv-pole-clamp` accessory face | profile → `commons-ward-pole`°: iv-pole-clamp, drip-chamber-holder | 2° | Consumes the accessory face `iv-pole-clamp` deliberately published as a separate interface — design intent realised, once D6 lets the graph see it | cq | T1 |
| 563 | `pill-blister-aid` | De-blistering aid for foil blister packs | Declared blister pocket 8–20 mm; ISO 9999 assistive | pocket → *(opens a new family)* | 0 | The unmet step in the commons' own medication cluster: organise, cut, insert — never *open* | cq | T1 |
| 564 | `cane-tip-adapter` | Ferrule adapter between mobility tube series and tips | 3/4–1 in (19–25 mm) mobility tube | socket → `commons-mobility-tube`°: mobility-accessory, walker-glide-cup, wheelchair-cup | 3° | Four mobility objects share one tube series with no adapter between sizes — and the series is `internal`, so the graph cannot see the family it already has | cq | T1 |

### 3.5 Infrastructure — 9 (#565–573)

| # | Slug | What | Standard(s) | CDG → mates | P | Demand | Eng | T |
| --: | :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| 565 | `wall-box-mud-ring` | Device-yoke mud ring and low-voltage bracket | US device yoke 83.3 mm (3.281 in) screw spacing **(verify)**; DIN 49073 Ø60 mm | bolt_pattern → **`wall-box`**: outlet-plate | 1 | Closes a singleton; both electrical-box objects derive nothing today. *The draft string named NEMA and mis-familied to `nema-stepper` — a live example of why §4.7 exists* | cq | T1 |
| 566 | `gland-lock-nut` | Backnut and sealing washer for cable glands | **IEC/EN 62444**; PG7–PG21, M12–M25 | thread → **`cable-gland`**: cable-gland | 1 | Closes a singleton; a gland ships as a pair in the real world and as a half here | cq | T1 |
| 567 | `emt-conduit-coupling` | EMT coupling and saddle strap | **ANSI C80.3** EMT 1/2–1 in | snap, socket → **`conduit`**: conduit-clip | 1 | Closes a singleton; the clip holds conduit and nothing joins two lengths | cq | T1 |
| 568 | `cts-pipe-standoff` | Standoff and manifold bracket for copper and PEX | CTS OD 1/2–1 in (15.9 / 22.2 / 28.6 mm) | socket → **`cts-pipe`**: pipe-clip | 1 | Closes a singleton and joins the plumbing cluster | cq | T1 |
| 569 | `duct-takeoff-collar` | Round-duct takeoff and reducer collar | SMACNA nominal round duct 4 / 5 / 6 in | socket → **`round-duct`**: duct-adapter | 1 | Closes a `profile`-only singleton with the socket the census says it needs | cq | T2 |
| 570 | `downspout-leaf-strainer` | Gutter-outlet and downspout leaf strainer | Round outlet series 50 / 68 / 75 / 87 / 100 / 110 mm; 2×3 & 3×4 in rectangular | socket → `downspout-outlet`°: stormwater-grate | 1° | Thickens the stormwater cluster; `downspout-adapter` is all-`internal`, so the family must be named for the edge to exist | cq | T1 |
| 571 | `valve-box-lid` | Irrigation and meter valve-box lid with a tool slot | 6 in & 10 in round valve box **(verify)** | socket, profile → *(opens a new family)* | 0 | Extends `water-meter-lid`'s municipal-access theme into the irrigation lane | cq | T1 |
| 572 | `busbar-insulating-shroud` | Terminal and busbar shroud on TS35 | DIN EN 60715 TS35; IEC 60529 IP2X | rail → `din-rail-35` (7) | 7 | Real electrical-safety function, and a second high-degree node in the DIN cluster | cq | T1 |
| 573 | `sign-post-splice` | Splice sleeve for U-channel and square sign posts | 3/8 in punched blank at 1 in pitch; 2/3/4 lb-ft U-channel; 1.75 / 2.00 / 2.25 in square tube | socket → `u-channel-post`°: sign-post-bracket | 1° | Rescues `sign-post-bracket`; damaged posts are spliced, not replaced | cq | T2 |

### 3.6 Agriculture — 8 (#574–581) — *under-served: 5 → 13*

| # | Slug | What | Standard(s) | CDG → mates | P | Demand | Eng | T |
| --: | :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| 574 | `drip-emitter-stake` | Stake and barb for 1/4 in micro-tube emitters | 1/4 in (6 mm) micro-tube; 1/2 in (16 mm) poly lateral | socket → `drip-irrigation`: drip-fitting, drip-manifold | 2 | Thickens a pair; the emitter stake fails first in every drip run | cq | T1 |
| 575 | `drip-line-end-closure` | Figure-8 and flush end closure for 16 mm lateral | 16 mm (0.600 in ID) drip lateral **(verify)** | socket → `drip-irrigation`: drip-fitting, drip-manifold | 2 | Completes the drip family into a real system: source, distribute, terminate | cq | T1 |
| 576 | `nft-channel-endcap` | NFT channel end cap and return port | 2 in (Ø50) & 3 in (Ø76) net-cup rim; 100 × 50 mm NFT channel **(verify)** | socket → `net-cup`: net-cup, net-cup-lid | 2 | Thickens a pair; the commons has the cup and the raft and not the channel | cq | T2 |
| 577 | `hive-entrance-reducer` | Langstroth entrance reducer and mouse guard | Langstroth 10-frame body inner width; bee space 6.0–9.5 mm; mouse-guard bar gap **(verify)** | profile → `langstroth`°: hive-frame-spacer | 1° | The seasonal companion to the only bee object in the commons; forces the D5 family pattern | cq | T1 |
| 578 | `plug-tray-dibber` | Dibber and soil-block former on plug-tray pitch | 1020 propagation tray (254 × 508 mm); 72 & 128-cell plug pitch | grid → `tray-1020`°: seed-tray | 1° | Propagation is the weakest agricultural step; also forces the D2 fix, without which this object inherits five false T-slot edges | cq | T1 |
| 579 | `trellis-vine-clip` | Vine and trellis clip for stake and wire | 8/10/12 mm bamboo and 1/2 in EMT stake; 2.0–2.8 mm trellis wire **(verify)** | snap → `conduit`: conduit-clip | 1 | Bridges the household plant objects into agriculture on a shared stake series | cq | T1 |
| 580 | `poultry-nipple-mount` | Bucket-mounted drinker nipple boss and drip cup | Self-tapping poultry nipple thread **(verify — measure before authoring)**; carboy/bucket bore | thread; socket → `bucket-bore`°: airlock-grommet, sharps-lid | 2° | Smallholder poultry watering is a printed-part staple; consumes the bucket-bore cluster | cq | T2 |
| 581 | `fodder-sprouting-tray` | Stacking sprouting and fodder tray with a drain grid | The `solar-dryer-tray` spigot–rim socket (0.35 mm per side); declared open-area ratio | socket, grid → solar-dryer-tray *(via D6; both sides are declared, neither is nameable)* | 0 | Reuses a published in-commons stacking interface instead of inventing one — the §7 honest-interface pattern, and a second argument for the `commons:` namespace | cq | T1 |

### 3.7 Energy — 6 (#582–587) — *under-served: 1 → 7*

| # | Slug | What | Standard(s) | CDG → mates | P | Demand | Eng | T |
| --: | :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| 582 | `mc4-unlock-key` | MC4 spanner and unlock key pair | **IEC 62852**; MC4 Ø16 mm nominal barrel | socket → `mc4`: mc4-holder, mc4-junction | 2 | Thickens a pair; the key is the one MC4 tool nobody has on a roof | cq | T1 |
| 583 | `pv-frame-edge-clip` | Module-frame edge clip for lead management | 30 / 35 / 40 mm anodised frame lip; H1Z2Z2-K 4–6 mm² lead | snap → `pv-frame-lip`°: pv-cable-clip | 1° | Consumes the frame-lip interface `pv-cable-clip` already publishes; array cable management is a code requirement, not a nicety | cq | T1 |
| 584 | `pv-rail-end-clamp` | Module mid- and end-clamp for rail mounting | 30–40 mm frame height; ISO 261 M8 tee bolt; 2020/2040 T-slot rail | profile → `t-slot-extrusion` | 1 | Joins the energy lane to the 7-member extrusion ecosystem | cq | T2 |
| 585 | `powerpole-housing-shell` | Powerpole-format housing shell and retaining clip | Anderson PP15/30/45 — **de-facto**, no issuing body **(verify)** | profile, snap → *(opens a new family)* | 0 | The de-facto DC interconnect of off-grid and emergency power; labelled de-facto rather than dressed as a standard | cq | T2 |
| 586 | `pack-busbar-cover` | Busbar and nickel-strip insulator for cell packs | 18650 Ø18.4×65 / 21700 Ø21.2×70; 0.15 mm nickel strip | grid → `battery-cell`: battery-holder | 1 | Thickens a 3-member family with the pack-safety part the commons lacks | cq | T1 |
| 587 | `din-energy-meter-shroud` | Terminal shroud for DIN-rail energy meters | DIN EN 60715 TS35; **DIN 43880** module width | rail → `din-rail-35` (7) | 7 | Puts the energy domain inside the commons' densest electrical ecosystem | cq | T1 |

### 3.8 Construction — 5 (#588–592) — *under-served: 1 → 6*

| # | Slug | What | Standard(s) | CDG → mates | P | Demand | Eng | T |
| --: | :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| 588 | `tile-levelling-clip` | Tile levelling clip and wedge system | ANSI A137.1 tile thickness and lippage reference; clip geometry de-facto **(verify)** | profile, snap → *(opens a new family)* | 0 | A very high-volume printed construction consumable, genuinely absent here | cq | T1 |
| 589 | `rebar-spacer-wheel` | Circular rebar spacer wheel | US bar #3 (9.5) / #4 (12.7) / #5 (15.9 mm); ACI 318 cover 20/40/50/75 mm | **snap** → `rebar`°: rebar-chair | 1° | Gives the lone construction cartridge a partner. *The census forced the geometry*: rebar-chair grips with a `snap`, and `socket↔snap` does not mate | cq | T1 |
| 590 | `formwork-tie-cone` | Tie-rod cone and spacer-tube plug for formwork | **DIN 18216** formwork ties; DW15 (Ø15 mm) & DW20 rod **(verify)** | socket, thread → *(opens a new family)* | 0 | Formwork consumables are printed on site; a real numbered standard behind them | cq | T2 |
| 591 | `scaffold-tube-cap` | Tube end cap and coupler spacer | **EN 12811-1 / EN 39** scaffold tube Ø48.3 × 3.2 / 4.0 mm | socket → *(opens a new family)* | 0 | One numbered tube OD serves scaffolding, handrail and temporary works | cq | T1 |
| 592 | `masonry-line-block` | Mason's corner line block and line pin | Modular brick 8 in / 65 mm metric course; 1.0–1.6 mm mason's line **(verify)** | profile → `brick-8mm-stud`: brick-tile | 1 | A trade tool bought, lost and re-bought; pairs with the brick module already in the commons | cq | T1 |

### 3.9 Consumer — 4 (#593–596) — *under-served: 2 → 6*

| # | Slug | What | Standard(s) | CDG → mates | P | Demand | Eng | T |
| --: | :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| 593 | `stemfie-beam` | Beam and plate set for the STEMFIE construction system | STEMFIE 10 mm block unit; 4 mm hole on 10 mm pitch (de-facto, open) | profile, bolt_pattern, thread → **`stemfie`**: stemfie | 1 | Closes a singleton; an open construction set with one part is not a set | scad | T1 |
| 594 | `brick-baseplate` | Construction-brick baseplate bridging the Gridfinity module | 8 mm stud pitch, Ø3.2 mm stud **(verify)**; Gridfinity 42 mm | grid → **`brick-8mm-stud`**: brick-tile; socket → `gridfinity` (3) | 4 | Closes a singleton **and** bridges two grid ecosystems on one plate | scad | T2 |
| 595 | `suitcase-wheel-housing` | Spinner-luggage wheel housing and axle block | 50 / 54 / 60 mm luggage wheel **(verify)**; ISO 15 608 bearing, 6 mm axle | socket → `bearing-608` (6) | 6 | Luggage wheels are the archetypal unrepairable consumer failure; lands in a 6-member family | cq | T2 |
| 596 | `skateboard-riser-pad` | Deck riser and shock pad | Truck pattern 2.125 × 1.625 in ("new school") / 2.5 × 1.625 in ("old school"); 10-32 UNF — **de-facto (verify)** | bolt_pattern → *(none)* | 0 | **Ranked on demand alone, and flagged as such (§5.4):** a genuine de-facto pattern with no issuing body and no partner in the commons | cq | T1 |

### 3.10 Hybrid 2, soft-robotics 1, wearable 1 (#597–600)

| # | Slug | Domain | What | Standard(s) | CDG → mates | P | Demand | Eng | T |
| --: | :-- | :-- | :-- | :-- | :-- | --: | :-- | :-- | :-- |
| 597 | `magnetic-tool-coupler` | hybrid | Quick-change magnetic tool coupler across a robot flange and a shaft | ISO 9409-1-50-4-M6; Ø8–16 mm NdFeB | bolt_pattern → `iso-m6`: sentinel-gripper-hyperobject; socket → magnetic-coupling *(via D6)* | 1 | Turns #523 into a system; magnetic tool change is the soft-robotics cluster's missing verb | cq | T3 |
| 598 | `tendon-routing-pulley` | hybrid | Tendon guide pulley block for cable-driven joints | ISO 15 608 bearing; 0.6–1.2 mm tendon **(verify)** | socket → `bearing-608` (6) | 6 | The commons has tendon-driven fingers and nothing to route a tendon through | cq | T2 |
| 599 | `pneumatic-quick-exhaust` | soft-robotics | Quick-exhaust and check-valve body on the commons barb series | Commons 2/3/4 mm tube-ID barb series; 4/6 mm push-in | socket → `commons-barb-series`°: bellows-actuator, pneu-net-finger, pneumatic-barb-port, suction-cup-bellows, vacuum-manifold-block | 5° | Five soft-robotics partners; actuator retraction speed is the family's stated weakness. Gated on D6, like #542 | cq | T3 |
| 600 | `hammer-loop` | **wearable** | Workwear hammer and tool loop, riveted or sewn | 20 / 25 / 38 / 50 mm webbing; rivet and eyelet fixing | profile, rail → `webbing-strap`: molle-clip, molle-pouch, nebulizer-mask-strap, paracord-jig, pet-hardware, strap-buckle; plus a `flange` on the sewn edge | 6 | **The entire demand pull.** `docs/fc400/index.json` rank 308 `painters-pant` claims `yantra4d/hammer-loop (co-create)` — the only FC hardware claim across four bands that does not resolve (§2.2) | cq | T2 |

### 3.11 Declared siblings (census discipline)

Eleven proposed slugs share tokens with a live cartridge. Each is a sibling on a different
physical interface, not a duplicate. Naming them is the census rule from
`WEARABLES-COVERAGE.md` §1 applied to the whole commons.

| Proposed | Existing | Why it is not a duplicate |
| :-- | :-- | :-- |
| `led-channel-corner` | `led-channel` | The channel is the extrusion profile; this is the joiner that receives it |
| `french-cleat-keyhole-plate` | `french-cleat` | The cleat is the rail; this is a hung plate that also presents keyholes |
| `bucket-lid-adapter` | `sharps-lid-adapter` | Different finish families: pail mouth + PCO 1881 vs GPI 63/70/89-400 clinical jars |
| `rod-cross-clamp` | `rod-rig-clamp` | Ø12 mm lab and optical rod vs 15 mm LWS camera rod — unrelated standards |
| `din-rail-end-stop` | `din-rail-clip` | The clip is a carrier that mounts *to* rail; this terminates and spaces *the* rail |
| `mic-stand-thread-adapter` | `thread-adapter-kit` | Stand threads (5/8-27, 3/8-16 BSW, 1/4-20) vs plumbing (GHT/NPT/BSP/M20/M24) |
| `iv-pole-tray` | `iv-pole-clamp` | Consumes the clamp's published accessory face; it never touches the pole |
| `sign-post-splice` | `sign-post-bracket` | The bracket attaches signage; the splice joins two post sections |
| `pv-frame-edge-clip` | `pv-cable-clip` | The cable clip carries the lead; this clips the frame lip, at a different section |
| `magnetic-tool-coupler` | `magnetic-tool-strip` | Robot-flange tool change vs a wall-mounted knife strip; unrelated geometry |
| `broom-clip-rail` | `magnetic-tool-strip` | Mechanical spring capture of round handle stock vs magnetic capture of flat steel |

### 3.12 The top ten by leverage

Leverage = measured partner count (P), weighted by how many one-member families the object
closes, and by whether the edges are genuine-standard or merely fastener-size. Ties broken
by demand strength.

| Rank | Slug | P | One line |
| --: | :-- | --: | :-- |
| 1 | `bucket-lid-adapter` (#519) | 11° | Highest measured yield in the wave: joins the invisible bucket/carboy-bore cluster to the 9-member PCO 1881 family in one lid |
| 2 | `pi-din-carrier` (#537) | 9 | Bridges the 2-member `rpi-mount` family into the 7-member DIN rail family — nine partners, every one a genuine standard |
| 3 | `mic-stand-thread-adapter` (#543) | 7° | Closes two singletons (`mic-thread-5/8-27`, `unc-3/8-16`) and joins `unc-1/4-20`, the 17-member largest family; its `tripod-hub` edge is what D1 rescues |
| 4 | `din-rail-end-stop` (#536) | 7 | Seven existing DIN EN 60715 members mate a single rail interface, at T1 effort |
| 5 | `hose-barb-tee` (#542) | 5° | Makes the soft-robotics family real: five members publish a `profile` series that nothing consumes as a `socket` |
| 6 | `pneumatic-quick-exhaust` (#599) | 5° | The same five partners from inside the domain, and the actuator function the family is missing |
| 7 | `busbar-insulating-shroud` (#572) | 7 | A second high-degree DIN node with a real electrical-safety function |
| 8 | `french-cleat-keyhole-plate` (#503) | 2 | Two singletons (`french-cleat`, `keyhole-hanger`) closed by one T1 cartridge — the best edge-per-effort ratio |
| 9 | `brick-baseplate` (#594) | 4 | Closes `brick-8mm-stud` and bridges it into the Gridfinity ecosystem on one plate |
| 10 | `filament-spool-adapter` (#541) | 6 | Highest-demand accessory for this commons' own audience, landing inside the 6-member `bearing-608` family |

*Just outside:* `v-belt-idler-arm`, `suitcase-wheel-housing`, `tendon-routing-pulley`
(6 each, all `bearing-608`), `er-collet-tray` and `bit-holder-block` (6 each, Gridfinity),
and `hammer-loop` (6, `webbing-strap`) — which is here on demand, not on leverage.

### 3.13 Distribution, and the balance check

| Domain | 500 | +wave 6 | 600 | Share 500 → 600 |
| :-- | --: | --: | --: | :-- |
| household | 125 | 22 | 147 | 25.0% → 24.5% |
| industrial | 108 | 20 | 128 | 21.6% → 21.3% |
| commercial | 75 | 13 | 88 | 15.0% → 14.7% |
| wearable | 72 | **1** | 73 | 14.4% → 12.2% *(demand-pulled; §2.2)* |
| medical | 44 | 9 | 53 | 8.8% → 8.8% |
| infrastructure | 33 | 9 | 42 | 6.6% → 7.0% |
| hybrid | 14 | 2 | 16 | 2.8% → 2.7% |
| uncategorized | 13 | 0 | 13 | 2.6% → 2.2% |
| soft-robotics | 7 | 1 | 8 | 1.4% → 1.3% |
| agriculture | 5 | **8** | 13 | 1.0% → 2.2% |
| energy | 1 | **6** | 7 | 0.2% → 1.2% |
| construction | 1 | **5** | 6 | 0.2% → 1.0% |
| consumer | 2 | **4** | 6 | 0.4% → 1.0% |
| **Total** | **500** | **100** | **600** | |

The four big domains each move by less than one percentage point — the balance the catalog
carries is kept. The only deliberate drop is wearable, and that is the standing ruling
working rather than drift: the shelf grows when an FC garment needs a solid we lack, and
exactly one does.

**Measured effect on the graph.** Running the shipped rules over the 100 proposed interface
sets, with the §4.5 fixes applied:

| Measure | Value |
| :-- | :-- |
| Derived partner links created | **230** |
| Objects deriving ≥1 partner | **86 of 100** |
| Objects deriving 0 (opening a *new* family) | 14 |
| One-member families closed (1 → 2) | **46 of 57** |
| One-member families left open | 11 — `beverage-can`, `bobbin-class-15`, `crown-cap-26`, `ferro-rod`, `license-plate`, `multiconnect`, `paracord-550`, `presser-shank`, `stir-bar`, `usb-sd-media`, `watch-movement` |
| Objects whose P depends on a §4.5 fix (marked °) | 13 |

The 11 left open are the honest tail: a second object in each would be filler.
`presser-shank` is deliberately skipped — a supply-side sewing tool violates the
demand-pull ruling — and `multiconnect` stays open because giving #502 a Multiconnect back
as well as a Multiboard one would be inventing a product, not observing a standard. The 14 objects deriving zero partners are the price of domain
broadening — every family starts at one member, and these open the ones agriculture,
construction and consumer will thicken in wave seven.

**Engine split: 97 CadQuery, 3 OpenSCAD** (#506, #593, #594 — dense repetitive CSG arrays).
**Tier split: T1 61 · T2 36 · T3 3 · T4 0** — deliberately no flagship. This wave buys
edges, not spectacle.

---

## 4. The wave protocol

The same model as waves one through five, with everything banked since.

### 4.1 Batching

Ten batches of ~8–12, dispatched to parallel worktree agents, sequenced so a batch never
contains two objects that mate with each other — a mating pair inside one batch hides
interface drift until integration:

```
W6-A household I (#501–511)      W6-F agriculture (#574–581)
W6-B household II (#512–522)     W6-G energy (#582–587)
W6-C industrial I (#523–532)     W6-H construction + consumer (#588–596)
W6-D industrial II (#533–542)    W6-I medical (#556–564)
W6-E commercial (#543–555)       W6-J infrastructure + hybrid/soft/wearable (#565–573, #597–600)
```

Exception, deliberately made: #542 and #599 both consume the barb series and are split
across W6-D and W6-J precisely so they cannot silently agree on a wrong barb dimension.

Each agent self-validates before handing back. The coordinator integrates, regenerates and
commits **per batch** — never once at the end.

### 4.2 The verification bar (unchanged, fail-closed)

- `y4d-spec check ./projects/<slug> --render` — the packaged CI gate from
  `hyperobjects-spec`: manifest, files, every (mode, part) **and every preset**.
- **Then the extremes sweep**: every (mode, part) at the min *and* max of every parameter,
  plus the all-min and all-max corners. Watertight, `body_count == 1`, meshed through the
  real `cq_runner` sandbox contract. Not optional — new-picks-A found two defects and
  frog-closure found three that the defaults-only lane passed clean.
- `scripts/qa/validate_manifests.py`, `check_licenses.py`, `compliance_audit.py`, and
  system `ruff` for cartridge Python.
- Quadrilingual at birth: en/es/fr/pt per RFC 0039 and the 2026-08-25 ratification. `es` is
  the register bar; `fr`/`pt` are real trade vocabulary, never a shipped machine draft.
- CERN-OHL-W-2.0 on every cartridge; every `compatible_with` reference must resolve.
- **Declare `difficulty`** in every manifest (§1.4) — the facet is dead at 0/466 today.

### 4.3 Catalog regeneration, per batch

`scripts/qa/generate_commons_catalog.py` is CI-enforced (`ci.yml` manifest-sync runs it with
`--check`), so a batch that adds cartridges **must** carry its regeneration.

> **Banked lesson (frog-closure, #60):** run the generator only with **all submodules
> checked out**. Against a worktree with submodules deinit'd it silently drops every
> submodule cartridge — one attempt rewrote the catalog to 432 entries and deleted 2799
> lines. Restore submodules first, then regenerate.

### 4.4 Geometry canon — the traps, and what each one cost

- **The tangent-torus trap (#60).** `ring ∪ tail` rendered an *open shell* because the ring
  tube spanned `z ∈ [0, ring_w]` and the tail spanned `z ∈ [0, tail_t]`, and at one
  parameter setting `ring_w == tail_t` — identical spans, coplanar faces, and OCC fused them
  tangentially. **Union overlaps, never tangents:** straddle the mating body in every axis
  so the intersection is volumetric for *every* combination, not just the default one. Two
  rounds of plausible fixes (a neck bound, a mouth-width bound) changed the volume not at
  all before bisecting the booleans found it. At risk in this wave: **#501, #511, #517,
  #521, #532, #542, #555, #566, #582, #591, #598, #599** — every ring, collar, tee, cap and
  joiner.
- **No pole singularities.** Domes and balls are lofts to a flat land, never a `sphere()`
  apex (walker-glide-cup, frog-closure).
- **Thread turns half-integer, never whole.** Grooves and threads are volumetric ribs.
- **Fillet before cut**; obround slots, never stadium approximations.
- **A no-op union is invisible.** `sharps-lid`'s chute extruded flush with the plate
  underside and floated inside the lid. Overlap into the mating body, then verify by
  section scan.
- **Clamp against the *final* value, not the input.** `frog-closure`'s `tail_w` outgrew the
  ring OD because it was capped before `loop_id` resolved. Order the clamps.
- **Record in the code which failure each clamp answers**, so a later edit knows what it is
  re-opening.
- `import cadquery as cq` at top; `PARAM(lambda: name, default)`; `result`; dispatch on
  `target_part`. `material_awareness` in the **top-level** `hyperobject` block;
  `project.hyperobject` stays minimal. Constraints use `expression`, not `rule`.
- **Never let a script write into submodule-backed projects.**

### 4.5 Graph hygiene, landed *with* the wave

The six defects in §1.4 are cheap and belong in this wave — 13 of the 100 derive nothing
without them, and D2's false edge would be inherited by #578 rather than fixed.

| Fix | Change | Unlocks |
| :-- | :-- | :-- |
| F1 (D1) | `1/4[\s-]?20` → `1/4["\s-]*20`; same for `3/8[\s-]?16` | `tripod-hub` joins `unc-1/4-20` (17) and `unc-3/8-16`; #543 |
| F2 (D2) | Drop `1020` from the `t-slot-extrusion` alternatives; add a `tray-1020` family | Kills the false `seed-tray` ↔ extrusion edge; #578 |
| F3 (D3) | Replace the bare `19mm` alternative in `miter-ttrack` with `19.05` | `camlock-latch` rejoins `cam-lock`; two false T-track edges removed; #516 |
| F4 (D4) | `iso\s*15` → `iso\s*15\b` | Stops any `ISO 15xxx` designation filing as a bearing; #525 |
| F5 (D5) | Add `rebar`, `langstroth`, `bucket-bore` families | #513, #519, #577, #580, #589 |
| F6 (D6) | A `commons:<series>` standard namespace that normalizes to a family, while the bare `internal` prefix keeps rejecting private geometry | #542, #562, #564, #581, #597, #599 — and makes the 5-member barb series, the ward-pole pair, the mobility-tube series and the magnetic bore visible for the first time |

Each is a one-line change in `_FAMILY_PATTERNS` (F6 needs a small branch in
`normalize_family`) with a unit test. Land them in the batch that depends on them, so the
edges appear in the same catalog regeneration.

### 4.6 A new lane: standards that do not normalize

Three of this plan's own draft interface strings mis-normalized during the planning pass —
a keyhole standard that said "M4" filed as `iso-m4`; a wall-box standard that said "NEMA"
filed as `nema-stepper`; an ER collet standard that said "ISO 15488" filed as
`bearing-608`; and a bottle-boss standard that said "M5" filed as `iso-m5` instead of
`bottle-cage-boss`. Each was caught only because the plan was verified by running the real
rules rather than by reading them — and the last two were caught on the second pass, after
the first pass had already been written up as correct.

**Proposal:** a `standards_normalize` lane that, for every non-`internal` declared standard,
fails the build if `normalize_family()` returns `None` **or** returns a family whose name
the author did not declare. An author who genuinely opens a new family declares it
explicitly (`family: new`). This converts the entire defect class in §1.4 into a gate, and
it is the single cheapest way to keep the graph honest at 600 and at 1000.

### 4.7 Bridge courtesy

Any cartridge here a Fashion Cabinet garment may consume — #600 `hammer-loop` certainly,
#581 and #513 plausibly — ends its README with the **Fashion Cabinet bridge** section
naming the garments expected to consume it and which parameters size the mating geometry,
per `WEARABLES-COVERAGE.md` principle 4. FC refreshes its own pinned snapshot; we do not
push into it.

---

## 5. The ratification ask (operator)

This index is **proposed**. RFC 0038 §10.3 ratified the wave sequencing; the hundred under
it has not had the evidence pass an FC band gets before its ranks are claimed. Five asks:

1. **Ratify or amend the hundred** (§3) — or ratify it as a *provisional band*: named, not
   reserved, with slots claimed only on green lanes, the FC-400/FC-500 pattern.
2. **Rule on the domain rebalance** (§3.13): agriculture 5→13, energy 1→7, construction
   1→6, consumer 2→6, financed by holding wearable at +1. This is the one place the wave
   deviates from "keep the domain balance the catalog already carries", and it deviates
   deliberately, by the stated rule — under-served *where real demand exists*.
3. **Rule on the `commons:<series>` namespace (F6, §4.5).** This is the largest single
   change proposed here and it touches the whole commons, not only this wave: 542 of 942
   interfaces are `internal` today and five genuinely shared series are invisible because
   of it. Three picks (#542, #599, #581) exist specifically to make that series real.
4. **Confirm the demand-pull reading** (§2.2): one unresolved FC claim across four bands
   means one wearable. If an FC-600 band is planned before this wave builds, draft its
   hardware claims first so any co-creations join this hundred rather than arriving as a
   tail.
5. **Approve or cut the two demand-only picks** — #520 `dishwasher-tine-cap` and #596
   `skateboard-riser-pad`. Both are honest: real geometry, real demand, **zero graph
   leverage**. Under "every object earns its place" they earn it on demand alone, and they
   are flagged rather than dressed up. If the bar is leverage-or-nothing, cut both and
   promote two of the 11 deferred singletons in §3.13.

Two things this document deliberately does **not** claim: that any of these objects is
built, and that any figure here was measured outside these repositories. Everything in §1
and every P in §3 is reproducible today from `docs/commons-catalog.json` and
`compatibility_graph.py`; everything in §2.2 is reproducible from the FC indices; and
everything marked **(verify)** is a designation or dimension that must be confirmed against
a primary source before a single line of geometry is written.

---

## 6. Data wanted and not found

Recorded so the next wave does not re-search for it:

- **No commons usage or telemetry data exists.** `docs/audits/*` holds browser, CI,
  production and codebase audits; none carries download, render or configure counts per
  cartridge. Every "demand" claim in §2 is therefore a *structural* argument (a standard
  exists, a cluster is incomplete, an FC band names it) and never a popularity measurement.
  A per-slug render/export counter would make wave seven's ranking materially better than
  this one's.
- **No `difficulty` data** (§1.4) — 0 of 466 manifests declare it, so no difficulty facet
  can inform selection.
- **No FC-600 band exists yet**, so the wearables demand pull could only be read from
  fc200–fc500. If FC-600 is drafted first, its co-creations belong in this hundred.
- **Fifth-hundred strategy was never written down.** Waves one through four have strategy
  documents; the fifth hundred exists only as commit messages (`fifth-hundred new picks A`
  and `B`, and `the closing six — 500`). Their reasoning was reconstructed from those
  messages for this document; there was no FIFTH-100-STRATEGY.md to inherit from.

---

*Companion to `FOURTH-100-STRATEGY.md` (graph-aware selection), `CDG-ACTIVATION-STRATEGY.md`
(why edges are the moat) and `WEARABLES-COVERAGE.md` (why the shelf is demand-pulled).
Executes RFC 0038 §3 under the §7 invariants.*
