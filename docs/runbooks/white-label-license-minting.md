# Runbook: Minting and Deploying a White-Label License Key

Audience: MADFAM operators provisioning a white-labeled Yantra4D instance for a
client (P1). Companion doc: [`docs/guides/white-labeling.md`](../guides/white-labeling.md)
covers branding variables, logo serving, and CORS; this runbook covers the
license JWT itself — what it must contain, how to mint and wire it, how strict
mode is rolled out, and what revocation actually does.

Everything in "What the code enforces" is grounded in the current source with
`file:line` citations. Everything Janua-side that this repo cannot verify is
explicitly marked **confirm with Janua admin**.

---

## 1. What the code enforces

The license key is a JWT placed in the backend env var `YANTRA4D_LICENSE_KEY`
(`apps/api/config.py:92`). It is validated on every `GET /api/config/client`
request by `apps/api/routes/core/client_config.py:76-92`, using the same
`decode_token()` path as user auth (`apps/api/middleware/auth.py:30-46`).

### Required claim set

| Claim | Requirement | Enforced at |
| :-- | :-- | :-- |
| `iss` | Must equal `JANUA_ISSUER` — default `https://auth.madfam.io` | `middleware/auth.py:42`, required by `auth.py:44`; default in `config.py:54` |
| `aud` | Must match `JANUA_AUDIENCE` — default `yantra4d-api` | `middleware/auth.py:43`; default in `config.py:56` |
| `exp` | Required; expiry ends the license term | `middleware/auth.py:44` |
| `sub` | Required; identifies the licensee principal (value is not otherwise inspected by the branding endpoint) | `middleware/auth.py:44` |
| `yantra4d_tier` | Must be literally `"pro"` or `"madfam"` for white-labeling to activate | `client_config.py:82` (resolve) + `client_config.py:86` (`has_tier(tier, "pro")`); resolution rules in `services/core/tier_service.py:47-61` |
| `tenant_id` (fallback: `org_id`) | Optional but recommended — returned to the Studio as `tenantId` for per-tenant localStorage namespacing | `client_config.py:83`, `client_config.py:118-119` |

Signature: **RS256** against the Janua JWKS. `JWT_ALGORITHMS` defaults to
`["RS256"]` (`config.py:58`); the JWKS URL defaults to
`{JANUA_ISSUER}/.well-known/jwks.json` (`config.py:141`) and keys are cached
for 3600 s (`middleware/auth.py:17`).

### Tier-resolution traps (why the claim must be exact)

`resolve_tier()` (`services/core/tier_service.py:47-61`) means a wrong or
missing tier claim fails *silently* into default branding:

- **Absent** `yantra4d_tier` on a valid token → `"essentials"` → below `pro`
  → white-label refused, endpoint still returns 200 with "Yantra4D" branding.
- Legacy value `"basic"` → mapped to `"essentials"` (`tier_service.py:22`,
  `37-44`) → refused.
- **Unknown** value (typo, e.g. `"Pro"`) → warning logged, falls back to
  `"essentials"` → refused.

The only accepted values for white-labeling are `pro` and `madfam`
(hierarchy at `tier_service.py:19`).

---

## 2. Minting the JWT via Janua

Known-fixed parameters (from this repo's verification side):

- Issuer: `https://auth.madfam.io` (unless the deployment overrides
  `JANUA_ISSUER`).
- Algorithm: RS256, signed with a key published in the Janua JWKS.
- Audience: `yantra4d-api` (unless the deployment overrides `JANUA_AUDIENCE`).
- Claims: the table in section 1, with `yantra4d_tier: "pro"` or `"madfam"`
  and a `tenant_id` naming the client.

**Confirm with the Janua admin before minting — this repo cannot verify any
of it:**

1. Whether Janua supports minting a long-lived *service/license* token (as
   opposed to a short-lived user session token), and through which admin API
   or console flow.
2. Whether custom `aud` (`yantra4d-api`) and custom claims (`yantra4d_tier`,
   `tenant_id`) can be set on such a token, and who is authorized to set them.
3. The maximum/allowed `exp` policy for service tokens, and the signing-key
   rotation schedule (rotation invalidates outstanding license keys — see
   section 5).
4. What `sub` should be for a client license (a dedicated service principal
   per client is the reasonable shape, but the convention is Janua's to
   define).

Do not hand-sign a token with an ad-hoc keypair: verification is strictly
against the live Janua JWKS, so only Janua-published keys work.

### Pre-flight validation

Before shipping the key to an environment, decode it (any JWT inspector, or
`python3 -c "import jwt, sys; print(jwt.decode(sys.argv[1], options={'verify_signature': False}))" "$TOKEN"`)
and check: `iss`, `aud`, `exp`, `sub` present; `yantra4d_tier` exactly `pro`
or `madfam`; `tenant_id` set. Then verify end-to-end against a running
backend (section 4, step 2).

---

## 3. Wiring the key into the deployment

- Env var: `YANTRA4D_LICENSE_KEY` (`config.py:92`), read by the **backend**
  service only — `yantra4d-backend`, served at `api.yantra4d.com` (Enclii
  PaaS; see the Deployment table in `AGENTS.md`). The Studio never sees the
  key; it consumes the resulting `/api/config/client` response.
- Companion (non-secret) vars on the same service: `PLATFORM_NAME`,
  `PLATFORM_LOGO` (`config.py:90-91`) — without a valid pro+ license these
  are ignored and the platform falls back to "Yantra4D"
  (`client_config.py:72-92`).
- For a dedicated client instance, also set `CORS_ORIGINS` and, if strictness
  is wanted, `YANTRA4D_LICENSE_REQUIRED` (section 4).

Per MADFAM Enclii-first doctrine (`AGENTS.md`), set the secret through the
**Enclii** web/API/CLI secrets flow for the `yantra4d-backend` service and
redeploy/restart it so the env is picked up. The raw-Kubernetes shape
(`kubectl create secret generic yantra4d-license --from-literal=YANTRA4D_LICENSE_KEY=…`
plus `envFrom: secretRef` on the backend Deployment, as shown in
`docs/guides/white-labeling.md`) is documented break-glass only, for when the
Enclii secrets adapter is unavailable — record the adapter gap if you have to
use it. Self-hosters on Docker Compose use the
`docker-compose.override.yml` pattern from the same guide.

Never commit the JWT to the repo, a manifest, or CI logs.

---

## 4. Strict-mode rollout (`YANTRA4D_LICENSE_REQUIRED`)

Default behavior is **fail-open for branding**: any validation failure logs a
warning and serves default "Yantra4D" branding with HTTP 200. With
`YANTRA4D_LICENSE_REQUIRED=true` (`client_config.py:27`), the endpoint
instead returns **403** when there is no key (`client_config.py:109-112`) or
when validation fails and no fresh cache exists (`client_config.py:104-107`).
The Studio calls this endpoint at boot, so a strict-mode 403 degrades the
client-facing app — treat enabling it as a production change.

Rollout order:

1. Deploy `YANTRA4D_LICENSE_KEY` + `PLATFORM_NAME` + `PLATFORM_LOGO` with
   strict mode **off** (unset/false).
2. Verify: `curl -s https://api.<client-domain>/api/config/client` returns
   the client's `platformName`, `platformLogo`, and `tenantId`. If it returns
   `"Yantra4D"`, check backend logs for
   `License key JWT validation failed` (`client_config.py:94`) or
   `License key valid but tier too low` (`client_config.py:92`).
3. Confirm the offline cache was written (section 5): `license_cache.json`
   under the backend `DATA_DIR` (`client_config.py:20-23`).
4. Only then set `YANTRA4D_LICENSE_REQUIRED=true` and re-verify step 2.
5. Rollback = unset the var (fail-open returns).

---

## 5. Cache behavior and the revocation reality

**Cache mechanics** (`client_config.py:20-57, 96-103`):

- On every *successful* validation the result (tier, tenant, brand values) is
  written to `LICENSE_CACHE_PATH` — default `DATA_DIR/license_cache.json`
  (`client_config.py:20-24`).
- The cache is read **only when live validation fails** (JWKS unreachable,
  token expired/invalid — the code does not distinguish), and is honored for
  up to `LICENSE_CACHE_MAX_AGE` = **86400 s / 24 h** (`client_config.py:24`,
  `37-38`) provided the cached tier is still pro+ (`client_config.py:98`).
- The cache lives on the backend pod's disk. If `DATA_DIR` is not on a
  persistent volume, a pod restart clears it — which is good for revocation
  lag but means a JWKS outage plus a restart drops branding (or 403s in
  strict mode).

**Revocation reality — state this to clients honestly:**

1. The token is a bearer-signed JWT. `decode_token()` checks signature,
   expiry, issuer, and audience only (`middleware/auth.py:38-45`) — there is
   **no per-request introspection or revocation-list call**. A minted token
   keeps validating until its `exp`, unless Janua rotates the signing key out
   of the JWKS.
2. Even after live validation starts failing, the **24 h offline cache**
   keeps white-label branding active for up to 24 hours past the last
   successful validation.

Effective revocation lag = (time until `exp`, or until JWKS key rotation)
**plus up to 24 h** of cache. Immediate kill requires touching the
deployment: remove/replace `YANTRA4D_LICENSE_KEY` and restart (and, if the
volume persists, delete the cache file — break-glass disk access). Mint with
an `exp` matched to the contract term rather than relying on revocation.

---

## 6. Private client demo kit (the tablaco pattern)

For client engagements that need a private, shareable demo *before or
alongside* a white-label deployment, the platform already supports a
three-part pattern, proven with the `tablaco` engagement:

1. **`unlisted` flag** — admin-togglable per project:
   `PATCH /api/admin/projects/<slug>/flags` with `{"unlisted": true}`
   (`apps/api/routes/users/admin.py:290-341`; allowed flags incl. `unlisted`
   at `admin.py:32`). Effect: the public project listing shows non-admins
   only demo/hyperobject projects **and not unlisted ones**
   (`admin.py:234-240`). Honest limit: unlisted is *hidden, not
   auth-gated* — anyone with the direct URL can open the project.
2. **`guest_render_limit` override** — the client's stakeholders can use the
   demo anonymously above the default guest rate (10/hr): set
   `project.guest_render_limit` (positive int) in the cartridge's
   `project.json`. Applied only to the `guest` tier by
   `get_render_limit_for_project()`
   (`apps/api/services/core/tier_service.py:88-106`).
3. **Admin-only public-link route** — `GET /api/admin/projects/tablaco/public-link`
   (`admin.py:344-363`) returns the storefront and studio URLs to share with
   the client; it is the only place the link is exposed, and it requires the
   `admin` role. Honest limit: the route is hardcoded to the `tablaco` slug —
   a new client demo needs its own route (or a generalization of this one).

Keep client cartridges out of the public Commons: list them in `NOT_COMMONS`
in **both** `scripts/qa/generate_commons_catalog.py` and
`scripts/qa/check_licenses.py`. CI (`check_licenses.py --strict-all`) fails
if an excluded cartridge ever appears in the published catalog.
