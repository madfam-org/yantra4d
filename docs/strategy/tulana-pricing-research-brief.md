# Tulana pricing-research brief — Yantra4D SKUs

**Governance rule (2026-08-12):** any pricing strategy for Yantra4D is forged by
tulana's benchmarking and pricing processes/protocols/research. This document
is the handoff: what to price, the anchors that already exist in code or
market data, and the constraints the research must respect. It deliberately
recommends **no numbers**.

## Status of the one figure currently visible

"from $9/mo" for Pro appears on the public pricing section
(`apps/landing/src/components/Pricing.astro`) and in the upgrade dialog
(`apps/studio/src/components/auth/UpgradeDialog.tsx`). It is **legacy product
copy** inherited from a component that was never mounted — not a validated
price. It stands as a provisional anchor until tulana's process replaces or
confirms it. Whether it should remain publicly visible during the research
window is an open call for Aldo.

## SKUs to benchmark

Tulana SKU keys use the double-underscore convention.

| SKU (proposed key) | What is being priced | Billing shape | Entitlement mechanism |
| :-- | :-- | :-- | :-- |
| `yantra4d__pro` | Pro tier: 150 backend renders/hr, all export formats incl. STEP, CadQuery engine, GitHub import + code editor, AI code editor (100 req/hr), print dispatch, manufacturing quotes | Monthly subscription via dhanam checkout (`plan=yantra4d_pro`) | Janua `yantra4d_tier` claim (see `docs/integrations/billing-entitlement-contract.md`) |
| `yantra4d__madfam` | Top tier: 500 renders/hr, 300 AI req/hr, GitHub sync | Subscription (`plan=yantra4d_madfam` already supported by `billing.ts`) | Same |
| `yantra4d__whitelabel` | Tenant license: custom branding, private catalog (unlisted + guest overrides), public demo links, hosted | Annual per-tenant license | `YANTRA4D_LICENSE_KEY` (complete mechanism; runbook: `docs/runbooks/white-label-license-minting.md`) |
| `yantra4d__fulfillment_take` | Take-rate on completed manufacturing quotes booked through Cotiza, and/or margin over ForgeSight p50 market pricing | % of order value | `cotiza_quotes` projection records `total_amount`/`currency` per order |
| `yantra4d__compute_credits` | Metered heavy compute beyond tier quotas (physics 20/hr, topology 20/hr, animation 10/hr today) | Credit packs (later phase) | Per-tier dynamic limits already enforced |

## Anchors and evidence already available

- **Entitlement matrix**: `apps/api/tiers.json` — the exact feature/quota
  deltas between tiers, i.e. the willingness-to-pay ladder to test.
- **Market material pricing**: ForgeSight benchmarks (p10/p50/p90 per kg, MXN,
  `market_verified` provenance) — the cost floor under any fulfillment margin.
  Caveat: the hardcoded fallback is USD with **no FX conversion**; quotes are
  only trustworthy on the live path.
- **Legacy anchor**: the $9/mo copy (above).
- **Pilot customer**: tablaco — the documented verified-quote flow
  (`docs/guides/tablaco-verified-quote-flow.md`) gives a real B2B reference
  case for `yantra4d__whitelabel` and `yantra4d__fulfillment_take`.
- **Cost side**: per-tier backend render quotas map to real server cost;
  318/324 commons cartridges can only render server-side, so the paywall is
  structural, not artificial — relevant to value-communication research.

## Constraints the research must respect

1. **Compliance**: the NC-restricted cartridges (`multiboard`, and
   `rugged-box` via vendored upstream — `license_exposure` field in
   `docs/commons-catalog.json`) are excluded from every paid surface; pricing
   scenarios must not assume revenue from them. CERN-OHL-W obligations
   (notice preservation, modified-design source availability) ride along on
   fulfillment.
2. **Honest labeling**: FEA stress and topology optimization are self-declared
   proxies, not solvers. No SKU may be priced as "simulation" until real
   solvers exist or the copy says "estimate".
3. **Currency**: MXN-first market via Cotiza/ForgeSight; USD appears only in
   the fallback path. An FX layer does not exist yet; cross-currency price
   presentation is blocked until it does.
4. **The commons stays free**: browsing, in-browser rendering, and STL export
   are the free tier by design — the pricing page states "the commons is free
   forever". Research scopes what sits above that line, not the line itself.

## Known caveat on the tulana side

Tulana's pricing engine was flagged (2026-07) for a circular
willingness-to-pay data-quality issue — validation inputs derived from its own
outputs. Before Yantra4D SKU research runs, confirm that remediation landed;
benchmarking outputs from before that fix should not seed these SKUs.

## Handoff outputs expected back from tulana

Per SKU: recommended price point(s) with the evidence trail, tested
alternatives, sensitivity to the tier deltas above, and — for
`yantra4d__fulfillment_take` — the take-rate band the tablaco pilot supports.
Those figures then flow into: dhanam plan configuration, the landing pricing
copy (both locales), the upgrade-dialog copy, and the white-label collateral.
