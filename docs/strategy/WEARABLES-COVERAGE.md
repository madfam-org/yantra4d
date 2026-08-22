# The Wearables Shelf — coverage strategy toward FC-1000

**Mandate (operator, 2026-08-22):** push the wearables section of the Hyperobjects
Commons to the limit, so the (eventual) 1000-object Fashion Cabinet commons finds
every solid geometry it needs already on this shelf, ready to bridge.

**The bridge mechanic this feeds:** FC references hard goods through
`notion.hardware_ref` against a vendored snapshot of our catalog; edge-sewn
hardware couples dimensionally (flange interfaces ↔ garment params). Every object
authored here is a future FC link — the shelf is the supply side of the
cross-commons contract (RFC 0037: integrate at contracts, separate at
implementations).

## Where the shelf stands

`domain: wearable` = **32 cartridges** after Wave T: the closures/adjusters of
Waves N.1–N.2 (rivet, jeans-button, d-ring, overall-buckle, suspender-clip,
toggle, magnetic-clasp, bra-ring-slider, collar-stay), the Wave T
garment-construction findings (belt-buckle, boning-stay, bra-underwire, cord-end,
garment-eyelet, hook-loop-tape, invisible-zipper, lacing-hook, sew-on-snap,
sew-through-button, trouser-hook-bar), the original trio (zipper, hook-and-eye,
shank-button-solid), and the 9-piece AM-fashion capsule (tpu-* panels,
corset-busk, epaulette-board).

The *fashion shelf* is bigger than the domain tag: FC's 52 live links also draw
on objects filed under other domains (snap-fit, strap-buckle, cord-lock,
bag-clip, belt-clip, carabiner, molle-clip, desk-grommet, zipper-pull,
watch-adapter, and the e-textile mounts). Coverage is measured by what FC can
*resolve*, not by the tag.

## The taxonomy, and where each category stands

| # | Category | Status |
| :-- | :-- | :-- |
| 1 | Sewn closures I (buttons, snaps, hooks, zips) | ✅ N-waves + T |
| 2 | Webbing & technical closures/adjusters | ✅ **Wave U** (side-release-buckle, ladder-lock, tri-glide-slider, cam-buckle, snap-hook-swivel, garter-clip) |
| 3 | Denim/utility hardware | ✅ N.1 |
| 4 | Intimates & structure (underwire, boning, stays) | ✅ T |
| 5 | Bag & leather hardware | ✅ **Wave V** (kiss-lock-frame, twist-lock-closure, chicago-screw, strap-end-tip, strap-ring, bag-feet) |
| 6 | Atelier tools (the sewing room) | ✅ **Wave W** (thimble, pattern-weight, bias-tape-maker, point-turner, buttonhole-spacer, magnetic-pin-dish) + existing bobbin-holder, needle-gauge, sewing-guide, warp-comb, yarn-guide |
| 7 | Display & garment care | ✅ **Wave X** (garment-hanger, shoe-tree, folding-board, belt-hanger, garment-clip, size-marker-ring) + the staging-solids S-wave ✅ merged (body-form figure/legs, garment-stand, lingerie-form, figure-child; display-armature C1/C2 queued per the S6 ruling) |
| 8 | AM-fashion printed textiles | ✅ capsule complete (9) |
| 9 | E-textile enclosures & mounts | ✅ **Wave Z** (seam-strain-relief, snap-electrode-carrier, seam-conduit-clip, battery-pocket-frame) + existing mounts |
| 10 | Millinery & head | ✅ **Wave Y** (hat-size-reducer, headband-blank, fascinator-base, veil-comb + adaptive aids below) |
| 11 | Adaptive & accessibility aids | ✅ **Wave Y** (button-hook-aid, zipper-loop-aid, magnetic-button-cover) |
| 12 | Shoe & leather II | ✅ **Wave Z** (heel-tip-blank, shoe-horn, boot-hook-puller); sam-browne stud deferred |

All six waves — U through Z, 38 cartridges — land with this document: the
campaign is COMPLETE. Per the operator ruling (2026-08-22), the shelf now grows
only by demand-pulled Group-B co-creation, not supply-side stockpiling.

## Principles (every wave, every cartridge)

1. **Census first.** `ls projects/` + catalog grep before naming a slug — the
   commons already holds 360+ objects; near-misses (d-ring vs strap-ring,
   board-feet vs bag-feet) must be siblings, not dupes.
2. **Real industry dimensions.** Webbing at 20/25/38/50 mm, nominal magnet and
   rivet sizes — the interface is only real if the numbers are.
3. **Flange only where fabric mates.** Edge-sewn/threaded hardware declares a
   flange-style interface whose parameters name the mating-edge params (FC's
   dimensional handshake consumes exactly this). Point-fixed hardware declares
   socket/snap/custom instead — an honest interface beats an impressive one.
4. **Every README ends with a "Fashion Cabinet bridge" section** naming the
   garments/notions expected to consume the object and which params size the
   mating geometry.
5. **Printable-first**, modes for meaningful variants, per-part dispatch ids
   aligned, watertight through the real sandbox (the T-wave verification bar:
   every (mode, part) pair, default + perturbed).
6. **CERN-OHL-W-2.0** and the house manifest structure, bilingual en/es.

## Definition of full coverage

Done means: **every garment family in a 1000-object Fashion Cabinet resolves its
hardware on this shelf** — no FC wave ever blocks on a missing solid. The
FC↔Y4D integration audit projected the fashion shelf at ~70 objects for that
scale; categories 1–8 complete put us at ~60 with U–X, and Y/Z close the tail.
When a new FC garment needs an object we lack, that gap is a Group-B co-creation
(FC need → new cartridge here), which is the co-evolution thesis working as
designed.
