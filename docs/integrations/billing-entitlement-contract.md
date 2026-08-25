# Dhanam ↔ Janua ↔ Yantra4D Billing & Entitlement Contract

Status: **draft spec (P2)** — the Yantra4D side of this contract is grounded
in code and cited `file:line`; the Dhanam and Janua sides are the *intended*
integration (asserted today by the admin UI and repo docs) and every
unverified detail is explicitly marked **UNKNOWN / to confirm**. No prices
appear here on purpose: price points are forged by tulana's benchmarking and
pricing processes (see `docs/strategy/tulana-pricing-research-brief.md`) and
then configured in Dhanam — never set in this platform's code. The "from
$9/mo" copy currently visible in the product is a legacy anchor pending
tulana validation.

> **A proposed answer now exists.** ADR-006 (`internal-devops/decisions/
> adr-006-entitlement-claim-and-tier-naming.md`, 2026-08-13) proposes the push
> model, the five-event set, `<product>_tier` as the claim-name pattern, and a
> `madfam` → `premium` rename. It also records a hazard this document did not:
> **`essentials` is a PAID tier on dhanam and a FREE tier here**, on shared
> identity infrastructure. Any dhanam→Janua mapping must be an explicit table,
> never a pass-through of the tier string.

Parties:

- **Dhanam** — billing: checkout, subscription lifecycle, payment webhooks.
- **Janua** (`auth.madfam.io`) — identity: mints the JWTs users present;
  is the only party that can change a user's claims.
- **Yantra4D** — consumer: gates features off a single JWT claim. It has no
  billing code paths and never talks to Dhanam directly.

---

## 1. The entire entitlement interface is one claim

Yantra4D resolves a user's tier from **only** the `yantra4d_tier` claim of a
Janua-verified JWT — `resolve_tier()` in
`apps/api/services/core/tier_service.py:47-61`. Grep-verified: `tier_service.py`
is the only production reader of that claim. Exact resolution semantics:

| Input | Resolved tier | Source |
| :-- | :-- | :-- |
| No token / invalid token | `guest` | `tier_service.py:54-55` |
| Valid token, **no** `yantra4d_tier` claim | `essentials` (authenticated baseline) | `tier_service.py:56` |
| `yantra4d_tier: "basic"` (legacy) | `essentials`, with a deprecation warning logged | `LEGACY_TIER_MAP`, `tier_service.py:22`, `37-44` |
| `yantra4d_tier` = unknown value | `essentials`, with a warning logged | `tier_service.py:58-60` |
| `yantra4d_tier` ∈ valid set | that tier | `tier_service.py:56-61` |

**Valid claim values**: `guest` / `essentials` / `pro` / `madfam`
(`TIER_HIERARCHY`, `tier_service.py:19`; mirrored by the Studio type
`Yantra4DTier` in `apps/studio/src/lib/billing.ts:14`). In practice a minted
token should carry `essentials`, `pro`, or `madfam` — `guest` is the
anonymous default, not something Janua needs to mint.

Consequences the billing side must understand:

- **Fail-degraded, not fail-closed**: a typo'd or unexpected claim value
  silently downgrades a paying customer to `essentials`. Janua must write
  exactly the strings above.
- The token is verified against Janua JWKS with issuer
  `https://auth.madfam.io` and audience `yantra4d-api`, RS256
  (`apps/api/middleware/auth.py:38-45`, defaults in `apps/api/config.py:54-58`).
- Yantra4D's `users` table mirrors the claim: on every authenticated request
  the user record's `tier` is overwritten from the JWT
  (`apps/api/services/core/user_service.py:27,37,46`). The DB is a cache of
  the claim, **never** an independent entitlement source — fixing a tier in
  the DB does nothing durable.
- The admin app states the intended ownership explicitly: "Tier assignments
  are managed through Dhanam billing webhooks"
  (`apps/admin/src/components/users/UserOverview.jsx:136-139`). There is no
  tier-editing endpoint in Yantra4D.

---

## 2. Checkout URL contract (implemented in Yantra4D today)

`apps/studio/src/lib/billing.ts` (`getCheckoutUrl()`, lines 19-31) is the
exact URL shape Yantra4D emits and therefore the minimum Dhanam checkout must
accept:

```
{DHANAM_CHECKOUT_URL}?plan=yantra4d_{pro|madfam}&product=yantra4d[&user_id=…][&return_url=…]
```

- Base URL: `VITE_DHANAM_CHECKOUT_URL` env at Studio build time, default
  `https://app.dhan.am/checkout` (`billing.ts:11-12`).
- `plan`: `yantra4d_pro` or `yantra4d_madfam` — literal SKU strings Dhanam
  must recognize (`billing.ts:25`).
- `product`: constant `yantra4d` (`billing.ts:26`).
- `user_id`: optional (`billing.ts:28`). The live caller passes the Janua
  SDK user id — `getCheckoutUrl('pro', user?.id, returnUrl)` in
  `apps/studio/src/components/auth/UpgradeDialog.tsx:35`, where `user` is a
  `JanuaUser` from `@janua/react-sdk`. **UNKNOWN / to confirm**: whether
  Dhanam expects exactly that identifier, and whether `JanuaUser.id` equals
  the JWT `sub` the webhook must ultimately target.
- `return_url`: optional; the caller passes `window.location.href`
  (`UpgradeDialog.tsx:34-35`) so the purchase can land back where the user
  was. **UNKNOWN / to confirm**: whether Dhanam redirects back to it after
  payment.

**Wiring status (code fact):** the mounted upgrade dialog
(`UpgradePromptProvider` → `apps/studio/src/components/auth/UpgradeDialog.tsx`)
uses `getCheckoutUrl()` as its primary CTA, with the marketing pricing page
link kept as a secondary action. (An earlier `UpgradeModal` component that
was never mounted has been removed.) The Studio side of this contract is
therefore live pending Dhanam-side confirmation of §6.

---

## 3. Purchase (upgrade) flow

```
User (Studio, tier=essentials)
  │ 1. opens checkout URL          — contract §2, billing.ts
  ▼
Dhanam checkout (plan=yantra4d_pro, product=yantra4d, user_id, return_url)
  │ 2. payment succeeds            — Dhanam internal, UNKNOWN mechanics
  ▼
Dhanam → Janua webhook: set yantra4d_tier=pro for that subject
  │ 3. claim update                — asserted by UserOverview.jsx:136-139 and
  │                                  AGENTS.md ("Dhanam webhooks to Janua auth");
  │                                  endpoint, auth, and payload shape UNKNOWN
  ▼
Janua: subsequent tokens for that user carry yantra4d_tier=pro
  │ 4. next token mint             — see §5 for the refresh lag
  ▼
Yantra4D backend: resolve_tier() → pro; user row mirrors claim on next request
```

Steps 1 and the final gating step are implemented and verifiable in this
repo. Steps 2-3 (Dhanam checkout semantics, the Dhanam→Janua webhook
endpoint/authentication/payload, retry and idempotency behavior) are
**UNKNOWN / to confirm** — no invented API shapes here; see §6.

## 4. Revocation (downgrade) flow

Cancellation, refund, chargeback, or non-payment must travel the same path in
reverse: Dhanam webhook → Janua removes or lowers `yantra4d_tier` → tokens
minted afterwards carry the lower claim → `resolve_tier()` gates accordingly
(absent claim on a valid token = `essentials`, `tier_service.py:56`).

- Yantra4D needs no code path for this and has none.
- **Timing**: a user keeps their old tier until their current JWT is replaced
  (§5). There is no push/invalidation mechanism in Yantra4D — the backend
  verifies signature/expiry/issuer/audience per request but never re-checks
  claims against Janua (`middleware/auth.py:38-45`).
- **UNKNOWN / to confirm**: which subscription lifecycle events Dhanam emits
  (end-of-period vs immediate cancellation, refund, dispute) and how Janua
  maps each to a claim change.
- Related but distinct: the white-label *license key* (a separate,
  operator-provisioned JWT) additionally has a 24 h offline cache on top of
  token validity — see `docs/runbooks/white-label-license-minting.md` §5.
  User-session entitlement has no such cache; the only lag is token lifetime.

## 5. Token-refresh implication

A claim change (upgrade **or** revocation) becomes visible to Yantra4D only
when the user presents a newly minted token. Worst-case entitlement lag in
both directions therefore equals the remaining lifetime of the token in the
user's hands.

- **Current Janua access-token lifetime: UNKNOWN / to confirm.** Do not
  design payment UX ("you're now Pro!") against an assumed number.
- **UNKNOWN / to confirm**: whether the Studio can force a token refresh
  after checkout returns (silent re-auth), which would make upgrades feel
  immediate; and whether Janua supports short-lived access tokens plus
  refresh tokens such that revocation converges quickly.

## 6. Open questions for the Dhanam / Janua teams

Dhanam:

1. Are `yantra4d_pro` / `yantra4d_madfam` registered as plans/SKUs, and is
   `product=yantra4d` meaningful to the checkout at `app.dhan.am/checkout`?
2. The Studio sends `user_id` = `JanuaUser.id` (from `@janua/react-sdk`) —
   is that the identifier Dhanam expects, is it required, and does it map to
   the JWT `sub` the webhook must target?
3. Is `return_url` honored post-payment? Any allowlist constraints?
4. Which lifecycle events are emitted (created, renewed, canceled,
   past_due, refunded, chargeback), with what retry/idempotency semantics?
5. Is there a sandbox/test checkout for end-to-end verification?

Janua:

6. Does the Dhanam→Janua webhook receiver exist today, and what is its
   endpoint, authentication, and payload contract?
7. Confirm Janua writes the exact strings `essentials` / `pro` / `madfam`
   into `yantra4d_tier` (never `basic`, never capitalized variants — see §1
   fail-degraded semantics).
8. What is the access-token lifetime, and is there a refresh-token or forced
   re-mint path the Studio can trigger after checkout?
9. On downgrade, is the claim removed or set to `essentials`? (Both resolve
   to `essentials` in Yantra4D — `tier_service.py:56` — but the convention
   should be explicit.)
10. Audit trail: where is the history of claim changes recorded for support
    disputes ("I paid but I'm not Pro")?

Yantra4D (follow-up this spec surfaces, not part of the contract itself):

11. If question 2 lands on a different identifier than `JanuaUser.id`,
    update the `getCheckoutUrl()` call site in `UpgradeDialog.tsx`
    accordingly.
