# Fashion Cabinet consumers — the bridge back-edge

Fashion Cabinet is the garment commons next door. Its cartridges are *notions* —
a zipper's placement math, a placket, a ligne-sized button hole — and its
guardrail is that the hard good itself is never re-implemented there: a notion
references a Yantra4D cartridge through a `hardware_ref` block and drives our
parameters from its own.

That bridge used to run one way. Fashion Cabinet vendors a pinned slice of our
`docs/commons-catalog.json` and resolves every `hardware_ref` against it, so
**their** CI notices when **we** move. Ours noticed nothing: renaming a
parameter here was green in this repo and red in theirs, days later, in a pull
request written by somebody who had never touched this one.

This page describes the other half of the pin.

| | |
|---|---|
| Vendored file | [`docs/interfaces/fashion-cabinet-consumers.snapshot.json`](../interfaces/fashion-cabinet-consumers.snapshot.json) |
| Upstream | `madfam-org/fashion-cabinet` : `docs/interfaces/yantra4d-consumers.json` (contract `yantra4d_consumers_v1`) |
| Script | [`scripts/qa/refresh_fc_consumers.py`](../../scripts/qa/refresh_fc_consumers.py) |
| CI lane | `refresh_fc_consumers.py --check`, in the `manifest-validation` job (blocking — reached by `ci-success`) |
| Today | 87 of our cartridges consumed, 299 linked consumers, 960 parameter references, 3 unlinked claims |

## What the back-edge says

Fashion Cabinet generates its half from its own cartridges and publishes it. Per
Yantra4D slug it lists the garments that consume that solid, the ids of **our**
parameters each one drives, the garment's manifest URL, and the Yantra4D commit
their claims were resolved against:

```jsonc
"consumers": {
  "bag-feet": [
    { "slug": "weekender-bag", "name": "Weekender Bag", "band": "FC-300", "rank": 207,
      "drives": ["foot_dia", "foot_h", "washer_dia"],          // parameter ids of ours
      "params_map": { "foot_dia": "foot_diameter", ... },      // ours <- their expression
      "manifest_url": "https://fashioncabi.net/api/v1/garments/weekender-bag" }
  ]
}
```

Two guarantees of theirs this repo leans on: everything under `consumers` is a
**real, linked** claim (a claim that is not yet a link appears under `wanted`
instead), and `drives` is the *Yantra4D* side — parameter ids of that cartridge,
not of the garment.

We vendor that document rather than fetching it, exactly as they vendor our
catalog: a submodule would import the other commons' whole implementation, and a
CI-time fetch would put the network inside a fail-closed lane. Neither repo
reads the other's source; each pins a slice of the other's published output.

The vendored file wraps their document unchanged in a pin:

```jsonc
{
  "pin": {
    "source_repo": "madfam-org/fashion-cabinet",
    "source_path": "docs/interfaces/yantra4d-consumers.json",
    "source_commit": "d57275176e634ac46e6700c9b516a0b7bb8f22fd",
    "source_schema_version": "yantra4d_consumers_v1"
  },
  "document": { ...their file, verbatim... }
}
```

No timestamp is recorded: the file changes when the content or the pin changes,
and never because it was rewritten.

> **The current pin is a branch commit.** `d5727517` is the Fashion Cabinet
> commit that first generated the back-edge; its pull request is open, not
> merged. Once it lands, re-vendor at a `fashion-cabinet` **main** commit so the
> pin names something that cannot be rebased away.

## What breaks CI

`python3 scripts/qa/refresh_fc_consumers.py --check` runs in the
`manifest-validation` job. It is offline and deterministic — it reads the
vendored snapshot, this repo's `projects/<slug>/project.json` manifests, and
`docs/commons-catalog.json`, and nothing else. For every **linked** consumer:

1. **The Yantra4D slug exists here.** A linked claim on a cartridge this repo
   does not have is a broken bridge, not a placeholder.
2. **Every parameter it drives is a real parameter of that cartridge.** This is
   the cross-bridged property: rename `foot_dia` on `bag-feet` and this lane
   names the garment that breaks —

   ```
   FAIL fashion-cabinet consumer 'weekender-bag' drives yantra4d 'bag-feet'
        parameter 'foot_dia', which projects/bag-feet/project.json does not
        declare (declared: boss_dia, flange_t, foot_diameter, ...)
   ```

3. **The vendored file is in canonical form** — byte-identical to its own
   sorted, stable re-serialisation. A hand edit to the snapshot is caught rather
   than trusted. (Formatting is what this catches; a *content* edit that still
   serialises canonically is caught by `--check-upstream`, below, which compares
   against the immutable commit the pin names.)

Parameters resolve from `projects/<slug>/project.json` when it is present, and
from the catalog only when it is not. That order matters: the catalog is
generated *from* those manifests, so trusting it first would let a rename pass
whenever the catalog had not been regenerated in the same commit — precisely the
drift this lane exists to catch. The fallback covers cartridges that live in
submodules, which CI checks out and a local clone often does not.

Parameters are a top-level array in the manifest schema — per-mode scoping is a
parameter's own `modes` / `visible_in_modes` list, not a parameters block inside
a mode — so every id a cartridge exposes, in any mode, is in that one array.

### What is reported and never enforced

Unlinked claims. Fashion Cabinet's `wanted` list is the honest record of
hardware a garment is waiting on, and a consumer entry may also carry an
explicit `linked: false`. Both are printed and neither can fail the lane:

```
note: wanted 'hammer-loop' (not built here yet) — requested by painters-pant
note: wanted 'frog-closure' (built here) — requested by changpao, jeogori-jacket
```

A co-create target nobody has built yet is a real state, not a failure. Reading
these is the cheapest demand signal this commons gets: `hammer-loop` is a solid
a garment is already asking for.

## Refreshing the pin

```bash
# from a local fashion-cabinet checkout — record the commit you took it from
python3 scripts/qa/refresh_fc_consumers.py \
    --from-path ../fashion-cabinet/docs/interfaces/yantra4d-consumers.json \
    --pin-commit <fashion-cabinet sha>

# or straight from a fashion-cabinet commit (network)
python3 scripts/qa/refresh_fc_consumers.py --from-commit <sha>

python3 scripts/qa/refresh_fc_consumers.py --check          # then re-run the lane
```

The pin must be a full 40-character commit sha; a branch name is refused,
because a pin that can move is not a pin. Vendoring is idempotent — the same
source at the same pin produces the same bytes.

A refresh that turns the lane red is the interesting case, and it is *not*
always our bug. Either the cartridge changed here and the garment must be
re-pointed there, or Fashion Cabinet published a claim we never satisfied. The
failure names both sides so the conversation starts with the facts.

### Drift against upstream

```bash
python3 scripts/qa/refresh_fc_consumers.py --check-upstream            # vs the pin
python3 scripts/qa/refresh_fc_consumers.py --check-upstream --against main
```

Network, and deliberately **not** in CI. Against the pin it proves the vendored
copy still matches the immutable commit it claims (a difference means the file
was altered here). Against another ref it previews what a refresh would bring.
Reads `raw.githubusercontent.com` unauthenticated and, when that cannot serve
the file, retries the Contents API with `GITHUB_TOKEN` / `GH_TOKEN` from the
environment — a commons can be private while it is being built.

## Tests

```bash
python3 -m pytest scripts/tests -q     # includes test_refresh_fc_consumers.py
```

The suite mutates the real vendored snapshot rather than inventing a fixture —
one parameter renamed, one slug pointed at nothing, one file reformatted — so it
cannot keep passing while the actual commons drifts underneath it. No test
asserts that a particular garment or cartridge is present: it pins the rule, not
today's membership of the bridge.

## See also

- [`docs/reference/manifest.md`](./manifest.md) — the manifest whose `parameters`
  array is the contract surface Fashion Cabinet resolves against.
- `docs/commons-catalog.json` — generated by
  `scripts/qa/generate_commons_catalog.py`; its per-cartridge `parameter_ids` is
  the half of this bridge that we publish.
- Fashion Cabinet's `docs/spec/v1/hardware-ref.md` — the normative contract for
  both directions, including the `yantra4d_consumers_v1` guarantees.
