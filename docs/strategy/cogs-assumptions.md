# Yantra4D cost-of-delivery assumptions (2026-08-13)

Input to `tulana/data/pricing/yantra4d/cogs.json`. The COGS estimator in tulana
is one of the few parts of that engine that is **de-circularized** — it does not
read MADFAM prices — so a cost floor is trustworthy evidence even while the
willingness-to-pay side is not (see `MONETIZATION_ROLE.md` D1/D3).

This document exists so nobody has to guess which numbers were measured and
which were assumed.

## What was measured

**Render wall-clock**, 2026-08-13, three runs per part of the `flange-plate`
graph cartridge through the real `cq_runner` sandbox:

| Part | min | median |
| :-- | --: | --: |
| `flange` (bore + 6-hole polar pattern + chamfer) | 5.18 s | 5.22 s |
| `blank` (bore + chamfer) | 4.77 s | 5.10 s |

Single-core, one subprocess per render. Measured on a development machine, not
the production worker; treat as the right order of magnitude, not a datacentre
benchmark. `flange-plate` is a deliberately mid-weight cartridge — simple
primitives render faster, the heaviest commons cartridges slower.

## What the compute costs

Node basis: a bare-metal AX41-class box at **$69/month** (the rate MADFAM
actually pays — see the builder-03 provisioning record), 12 hardware threads.

```
thread-hour cost   = $69 / (12 threads × 730 h)   = $0.00788
cost per render    = (5.2 s / 3600) × $0.00788    = $0.0000114
```

**About one hundred-thousandth of a dollar per render.** At 200 renders per
month — far above what a typical Pro user does — that is **$0.0023/month**.

## The finding: compute is not the cost driver

This is the result that should change the pricing conversation. On owned bare
metal, server rendering is effectively free at any plausible per-user volume.
Yantra4D's render quotas (10 / 30 / 150 / 500 per hour by tier) are therefore
**not cost controls — they are abuse controls and product differentiation.**

Two consequences:

1. **Do not price Yantra4D as cost-plus.** A margin over this COGS would price
   Pro at fractions of a peso. The price has to come from value and from what
   the market bears, which is exactly why the willingness-to-pay side matters
   and why D3 (zero WTP responses ever collected) is the real blocker.
2. **Raising render quotas is nearly free.** If a quota is costing a sale, the
   cost argument against raising it does not survive this arithmetic. The
   argument for keeping it is differentiation, which is a product decision, not
   a finance one.

## What is NOT measured, and would dominate if it were

The infrastructure floor above is a **floor**, not a COGS. These are unmeasured:

- **AI inference.** Pro grants 100 AI requests/hour, madfam 300. Every request
  is real LLM spend through the Selva gateway. At any realistic token count and
  provider rate this is **orders of magnitude larger than the render cost** and
  is very likely the true dominant variable cost. It needs the actual model and
  per-token rate, plus observed request volume.
- **Support.** Human time per account. voxa's model carries an explicit support
  slice; Yantra4D has no equivalent figure yet.
- **Actual usage distribution.** Everything above is per-render and per-request
  unit economics. Turning that into a per-account monthly figure needs render
  and AI telemetry per user, which is not currently collected in a form that
  answers "what does the median Pro account consume?"

**Do not treat the number in `cogs.json` as the cost of delivering a Pro
account.** It is the measured infrastructure component only, and it is
published to make the compute-is-negligible finding auditable — not to be
multiplied by a margin.

## Currency caveat

Tulana stores MXN centavos. Every conversion here uses the hard-coded 17.0
rate, because `FxObservation.count() == 0` and the FX cron has been green for
months without ever writing an observation (`MONETIZATION_ROLE.md` D4). The MXN
figures are therefore correct arithmetic over an unvalidated rate. At these
magnitudes the FX error is irrelevant; at SKU-price magnitudes it is not.

## Measurement plan to replace the assumptions

1. Instrument render duration and count per account (the render worker already
   emits per-job events; aggregate them).
2. Record AI request count and token usage per account at the Selva gateway.
3. Publish the provider's per-token rate as a config value rather than folklore.
4. Re-derive this document from those three, and only then treat the result as
   a cost of delivery rather than a floor.
