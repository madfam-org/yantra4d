# Bias Tape Maker

A 3D-printed **folded-channel bias tape tool** — generated with **CadQuery** (B-Rep). A
bias-cut strip feeds in the wide mouth, the tapering channel folds both raw edges to the
centre, and single-fold tape comes out the throat under the iron.

Part of the **Yantra4D Hyperobjects Commons** (an atelier-tools shelf finding).
Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part |
| :--- | :--- |
| **18 mm Tool** | `tool18` |
| **25 mm Tool** | `tool25` |
| **Both Tools** | `set` |

`tool18` and `tool25` are the two finished widths that cover most garment binding; `tool18`
also honours the `tape_width` parameter, so any finished width from 6 to 50 mm is reachable.
Feed a strip **twice** the finished width: 36 mm of bias for 18 mm tape, 50 mm for 25 mm.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:** Bias Strip Edge (`profile`) at the mouth and Folded Tape Throat
  (`profile`) at the exit. Both are genuine fabric-threading edges — cloth is drawn along
  them for the length of the tape — so they carry the parameters that size the cloth.

## Fabrication notes

The folding channel is a **single prismatic through-cut** whose plan view tapers from mouth
to throat and then runs straight out the back. It overshoots both end faces, so the channel
is genuinely open at both ends: no sealed void, and the shell stays **one solid** — there is
no separate top plate to weld on and no coplanar seam to crack. An open view slot runs along
the top so the folded edges can be seen and coaxed, exactly as on the metal originals.

The outer shell is tapered by cutting two wedges away from a plain block rather than lofting,
which keeps the whole part on stable prismatic booleans. Prints flat on its back with no
supports; the tail carries a pin slot (pin the strip to the ironing board to start) and a
hang hole.

`CERN-OHL-W-2.0`.

## Fashion Cabinet bridge

Fashion Cabinet garments finished with bias binding consume this: **necklines and armholes**
on unlined tops and dresses, **Hong Kong seam finishes** in unlined jackets, **quilt and
placemat edges**, and any curved raw edge FC's construction spec binds rather than faces.
The mating parameter is `tape_width` — FC's binding call-out (a finished width in mm) sets it
directly, and the garment's strip-cutting instruction is then `tape_width × 2`. `fabric_t`
couples to the fabric weight FC carries for the garment, so a heavy twill gets a slacker
channel than a lawn.
