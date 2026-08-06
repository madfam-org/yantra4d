# Rail Mount / Clamp

A two-piece clamp that grips a round boat, RV, or bimini rail so accessories ride on
standard tube stock. Bolt the split clamp around the rail, then mount a rod holder,
cup holder, or bare accessory plate. Sized by rail diameter (1 in / 25 mm and others).

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| 2-Part Rail Clamp | `clamp_base` | Both clamp halves, printed side by side; bolts around the rail. |
| Rod Holder Mount | `rod_holder_mount` | A clamp half fused to an angled tube for a rod, flag, or antenna. |
| Cup Holder Mount | `cup_mount` | A clamp half fused to a drained drink-holder ring on an arm. |

## Key Parameters

- **Rail Diameter** — outer diameter of the tube rail (1 in ≈ 25.4 mm).
- **Grip Clearance** — bore oversize per side; smaller values grip harder.
- **Clamp Wall / Length** — thickness around the rail and span along it.
- **Bolt Clearance** — clamp bolt hole diameter (M5 ≈ 5.0).
- **Rod Bore / Tilt** — rod-tube inner diameter and tilt from vertical.
- **Cup Bore** — drink-holder ring inner diameter.

## Printing Notes

Print in PETG or ASA for UV and moisture resistance in a marine environment. The clamp
halves nest around the rail and pull together with two bolts; a smaller grip clearance
plus a strip of rubber tape prevents slip.

## Hyperobject Profile

- **Domain:** hybrid (marine / RV / mobile living).
- **CDG interfaces:**
  - `rail_clamp_bore` (`socket`) — the round-rail bore, standard **1 in / 25 mm round rail**, driven by `rail_dia`, `grip_fit`, `clamp_len`, `bolt_dia`.
  - `accessory_bolt_top` (`bolt_pattern`) — the flat bolt face every accessory shares (`internal`).
- **Material awareness:** tolerance-by-material (tighter grip clearance for stiff PETG/ASA).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** replaces costly proprietary marine rail hardware with a printable
  clamp sized to whatever rail is on hand, so any round rail becomes a gear mount.
