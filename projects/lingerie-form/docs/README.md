# Lingerie Form

A parametric **intimates display form** — the smooth bust-and-hip body the
[Fashion Cabinet](https://github.com/madfam-org/fashion-cabinet) soft-goods
commons stages bras, briefs, camisoles, and slips on. Sibling of
[`body-form`](../../body-form/docs/README.md), and like it deliberately an
**abstract form, not a figure**.

## Why it is its own cartridge

It would be cheaper to trim the dress form to a shorter torso and call it done.
That would be wrong, and the reason is one ring.

On intimates the **fit is the product**, and a bra is fitted on *two* numbers —
the bust and the **underbust band** beneath it. A dress form has no underbust
ring: loft straight from waist to bust and you get a cone, the band floats, and
a garment that would not fit still looks fine on the stand. So this form carries
the underbust as a first-class measured ring, which makes it a genuinely
different anatomy rather than a shorter one.

The rest of the difference is subtraction. The form runs **upper chest → upper
thigh** and stops: everything above would only hide a strap, everything below
would only hide a leg line. There is **no post, no base, no stand hardware** —
it is closed flat at both ends and stands unaided on its own bottom face.

## How it's built

The same machinery as `body-form`, and deliberately so — one **ruled loft
through elliptical cross-sections** whose perimeters equal their landmark
girths, via a Ramanujan perimeter fit. Linear (ruled) loft is used on purpose:
a linear interpolation between two ellipses can never bulge wider than either,
so every measured ring is dimensionally exact (verified: hip / waist /
underbust / bust all measure their girth to within 0.02%). On a bra band that
guarantee is the difference between a form that fits and one that lies.

**Bust shaping.** Girth alone cannot make a bust — a wider ellipse just spreads
the fullness sideways into the ribs. Two things fix that. The bust band is
lofted at a **higher depth:width ratio** than its neighbours, which sends the
extra circumference forward instead of outward; and the whole band is **offset
forward on Y** by `bust_projection`, ramping in below the band and back out
above the apex so the projection blends rather than steps. The result is a
rounded front and a quiet back — a form, not a barrel. At the default size the
apex sits ~158 mm proud of centre while the back stays at ~106 mm.

**Vertical stations.** The form is proportioned off *measured spans*
(`underbust_to_waist`, `waist_to_hip`) rather than a whole-body height, because
it has neither head nor legs to proportion against. The measured stations fix
the middle; the top and bottom rings absorb the remaining `torso_length`. Each
end carries its own minimum, so a too-short `torso_length` grows the form past
the request instead of crushing the above-bust shelf or stopping short of the
brief line — the proportions are the contract, the overall height is not.

Watertight throughout (Yantra4D scar tissue respected): a pure additive loft,
**no cuts at all**, so the fillet-after-cut OCCT segfault path does not exist
here; both ends close on the loft's own flat caps, never a sphere cap (the
pole-fan singularity that reads non-watertight); and the hanging tab is a solid
prism rooted well down **into** the closed solid top — generous overlap, one
connected volume, no trapped cavity.

## Modes

| mode | what it is |
|------|-----------|
| `form` | the bare intimates form, flat top and flat bottom, stands unaided |
| `hanger_tab` | the same form with a small integrated hanging tab, so it can hang in a display as well as stand |

## Landmark-ring interfaces (CDG)

The manifest's `hyperobject.cdg_interfaces` expose the measured rings as
`surface` interfaces, each mapped to the ISO-8559 landmark it carries:
`upper_chest_ring`, `bust_ring`, **`underbust_ring`**, `waist_ring`,
`hip_ring`, `thigh_ring`. These are the surfaces a Fashion Cabinet garment's
"dressed form" view wraps its pieces onto.

Parameter names are shared with `body-form` wherever the same measurement is
meant — `bust_girth`, `waist_girth`, `hip_girth`, `thigh_girth` — so the
Fashion Cabinet measurement mapping extends to this solid unchanged. The
`measurement.code` on every measured parameter is drawn from the canonical
ISO-8559 landmark enum in
`fashion-cabinet/packages/schemas/body-measurements.schema.json` (note
`upper_chest_girth` carries the canonical code `chest_bust_girth`, and
`underbust_girth` is canonical as spelled — not `under_bust_girth`). The two
vertical spans carry no `measurement` block, because there is no canonical
ISO-8559 code for them.

## Measurements

Drive it with the ISO-8559 girths (mm, full-body circumferences): `bust_girth`,
`underbust_girth`, `waist_girth`, `hip_girth`, `upper_chest_girth`,
`thigh_girth`, plus the vertical spans `torso_length`, `underbust_to_waist`,
and `waist_to_hip`. Shaping knobs (`bust_depth_ratio`, `bust_projection`,
`seat_depth_ratio`) are advisory — the measured rings stay authoritative. Size
presets ship for women's S / M / L / XL; a made-to-measure set overrides any of
them. It renders to **GLB/GLTF** (the web-3-D format the studio consumes) as
well as STL / STEP / 3MF / OBJ for fabrication.

Official visualizer and configurator: **Yantra4D**.
