# Cross-ecosystem interventions owed to Yantra4D

Everything on this page is **outside this repository**. Each item was found
while working on Yantra4D, is blocking or degrading something here, and can
only be resolved by another platform's owner or from the operator console.

Nothing here is a code change to Yantra4D. The Yantra4D side of every item is
already built and cited below; what is missing is the other end.

Each item carries a **verification command** that reports the current state.
Run the command to know whether the item is still open — do not rely on this
page's status, which is only accurate as of 2026-08-13.

---

## Y1 — `yantra4d_tier` claim contract (dhanam → Janua) · **blocking all revenue**

**Impact.** No user can reach a paid tier. Claims arriving without
`yantra4d_tier` resolve to `essentials`
(`apps/api/services/core/tier_service.py:51-56`), so every paid capability —
CadQuery engine, the graph engine, STEP export, 150 renders/hour, print
dispatch, manufacturing quotes — is unreachable by a real customer no matter
what they pay. Checkout links out to dhanam and the entitlement never returns.

**What is already built here.** Tier resolution, the feature matrix
(`apps/api/tiers.json`), gating decorators, and checkout URL generation
(`apps/studio/src/lib/billing.ts`). The full contract, with the Yantra4D side
grounded in `file:line` and the dhanam/Janua sides marked UNKNOWN, is
`docs/integrations/billing-entitlement-contract.md`.

**What is owed.** Dhanam must notify Janua on subscription change, and Janua
must mint `yantra4d_tier` into the JWT it issues. One claim, four values:
`guest` / `essentials` / `pro` / `madfam`.

**Verify (no credentials needed — proves the gate is live and closed):**

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://api.yantra4d.com/api/render -H 'Content-Type: application/json' -d '{"project":"spacer-block","mode":"spacer","parts":["spacer"],"parameters":{},"export_format":"stl"}'
```

`403` means the gate works and the tier is still unreachable. The contract is
satisfied when a subscribed user's token carries the claim — check with:

```bash
curl -s https://api.yantra4d.com/api/me -H "Authorization: Bearer $YANTRA4D_TOKEN" | python3 -m json.tool
```

---

## Y2 — Price points for five SKUs (tulana) · **blocking honest pricing**

**Impact.** The live pricing page shows "from $9/mo" for Pro. That number
exists nowhere in this repository except copy — it is inherited product text,
not a validated price. Per standing governance, price points are forged by
tulana's benchmarking and pricing processes and never set ad hoc here.

**What is already built here.** The handoff brief, including the five SKU keys
(double-underscore convention), the entitlement deltas to price against, the
compliance constraints, and the known caveat about tulana's circular
willingness-to-pay data: `docs/strategy/tulana-pricing-research-brief.md`.

**What is owed.** Recommended price points with evidence for
`yantra4d__pro`, `yantra4d__madfam`, `yantra4d__whitelabel`,
`yantra4d__fulfillment_take`, `yantra4d__compute_credits`.

**Also unresolved:** the `madfam` tier exists in `apps/api/tiers.json` and is
absent from the public pricing page. Whether it is a sellable tier or an
internal one is a product decision, not a code defect.

**Verify (shows the anchor still in place):**

```bash
curl -s https://yantra4d.com/ | grep -oiE '(desde|from) \$[0-9]+/(mes|mo)' | sort -u
```

The anchor is localised (`desde $9/mes` on the Spanish page, `from $9/mo` on
`/en/`), so match both — a `/mo`-only pattern silently finds nothing on the
default locale and reads as "already resolved".

---

## Y3 — Cotiza and ForgeSight production credentials · **degrading fulfillment**

**Impact.** Manufacturing quotes and material pricing are the fulfillment
revenue path. Without the shared secrets, inbound webhooks fail signature
verification and are rejected; without a reachable ForgeSight, pricing falls
back to hardcoded USD values with **no FX conversion**, so quotes shown in a
MXN-first market are not trustworthy on the fallback path.

**What is already built here.** Both receivers, HMAC-SHA256 verified and
idempotent: `apps/api/routes/integrations/cotiza_webhook.py` (which also
projects quote events into `cotiza_quotes`) and
`apps/api/routes/integrations/forgesight_webhook.py`.

**What is owed.** `COTIZA_WEBHOOK_SECRET` and `FORGESIGHT_WEBHOOK_SECRET` set
in the production environment, matching the values held by each sender.

**Verify (unsigned request must be rejected):**

```bash
curl -s -o /dev/null -w 'cotiza=%{http_code}\n' -X POST https://api.yantra4d.com/api/webhooks/cotiza -H 'Content-Type: application/json' -d '{"event_type":"quote.completed"}'
```

`401`/`403` is correct behaviour whether or not the secret is set — a `500`
or `200` here is a defect worth reporting back to this repo.

---

## Y4 — `docs.yantra4d.com` was never deployed

**Impact.** Documentation links in the product and README point at a hostname
that does not resolve. `README.md:159` already states this honestly rather
than pretending otherwise.

**What is owed.** Either deploy the docs site or retire the hostname and
repoint the links at the repository's `docs/` tree.

**Verify:**

```bash
curl -s -o /dev/null -w '%{http_code}\n' --max-time 10 https://docs.yantra4d.com/ || echo "does not resolve"
```

---

## Y5 — Secret rotations owed (carried from earlier work)

Not Yantra4D-specific, recorded here because they were surfaced during this
work and remain outstanding:

- **`NPM_MADFAM_TOKEN`** rotation, owed since the internal-devops
  stabilization sweep. This repo consumes the private registry through
  `apps/studio/.npmrc`, so a rotation must land here at the same time.
- **Leaked tulana secrets** (42 of them) identified during the fortuna
  activation work.

These belong to whoever holds the credential store; they are listed so they
are not lost, not because Yantra4D can act on them.

---

## What is *not* on this page

Items that are Yantra4D's own work — the node editor, further graph
cartridges, landing polish, translation coverage, replacing the SQLite
fallback with Postgres — are tracked in the repository and are being worked
here. This page is only for things that require another team or the operator
console.

Known Yantra4D-side limitations that are **correctly labelled and not defects**:
FEA stress and topology results are declared proxies rather than solver
output, and the physics worker emits synthetic progress frames. Any future
copy that upgrades these to "simulation" or "verified" without real solvers
behind them would be the defect.
