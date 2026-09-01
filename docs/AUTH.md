# Authentication — Janua Integration

Yantra4D authenticates users through Janua, a self-hosted OIDC provider in the MADFAM ecosystem. This document covers the Flask middleware layer, decorator-based access control, and configuration.

---

## Architecture

```
Browser / API Client
  |
  |  Bearer token in Authorization header
  v
Flask Application
  |
  |  auth.py middleware
  |  (JWKS validation, role/tier checks)
  v
Route Handler (authenticated request context)
```

Janua issues RS256-signed JWTs. The Flask middleware validates tokens using Janua's JWKS endpoint. Decorators on route handlers enforce authentication, role, and subscription tier requirements.

---

## Middleware

The auth middleware lives at `apps/api/middleware/auth.py` and provides four decorators:

### `@require_auth`

Enforces authentication. Extracts the Bearer token from the `Authorization` header, validates it against the Janua JWKS endpoint, and injects the decoded token payload into the request context.

Returns HTTP 401 if no token is present or if validation fails.

```python
@app.route("/api/projects")
@require_auth
def list_projects():
    user_id = g.auth_payload["sub"]
    # ...
```

### `@require_role(role)`

Requires a specific role claim in the token. Must be used after `@require_auth`. Returns HTTP 403 if the user does not have the specified role.

```python
@app.route("/api/admin/users")
@require_auth
@require_role("admin")
def admin_list_users():
    # ...
```

### `@require_tier(min_tier)`

Requires a minimum subscription tier. Tier values are compared numerically. Returns HTTP 403 if the user's tier is below the minimum.

```python
@app.route("/api/export/step")
@require_auth
@require_tier("pro")
def export_step_file():
    # ...
```

### `@optional_auth`

Decodes and validates the token if present, but does not reject the request if no token is provided. Useful for endpoints that behave differently for authenticated and anonymous users.

```python
@app.route("/api/models/<id>")
@optional_auth
def get_model(id):
    if g.auth_payload:
        # Return full model with edit permissions
    else:
        # Return read-only public view
```

### `@require_render_scope`

Requires the `yantra4d:render` scope — **on machine tokens only**. Layer it directly
below `@optional_auth`, which must already have populated `request.auth_claims`.

```python
@render_bp.route('/api/render', methods=['POST'])
@optional_auth
@require_render_scope
def render_stl():
    # ...
```

Applied to `/api/render`, `/api/render-stream`, `/api/estimate`, and
`/api/render-cancel`. The generic form is
`require_scope_for_machine_tokens("<scope>")`.

---

## Machine tokens and render scope

Janua mints two token shapes against the `yantra4d-api` audience:

| | Human (`authorization_code` / `refresh`) | Machine (`client_credentials`) |
|---|---|---|
| `sub` | user UUID | `service-account:{client_id}` |
| `token_use` | *(absent)* | `client_credentials` |
| `actor_type` | *(absent)* | `service_account` |
| `client_id` | *(absent)* | the OAuth client id |
| `scope` | *(absent)* | space-delimited, e.g. `yantra4d:render` |
| `yantra4d_tier` | from the user's entitlements | **derived from the `yantra4d:` scope namespace** (`madfam`) |

Source of truth: janua `apps/api/app/routers/v1/oauth_provider.py`
(`_get_client_credentials_claims`, `_handle_client_credentials_grant`).

The last row is why this check exists. Janua synthesises `yantra4d_tier: "madfam"`
for any machine client holding a `yantra4d:`-namespaced scope, but the *specific*
scope was never checked here — so a machine client provisioned for a different
`yantra4d:` capability could render, and the `yantra4d:render` scope Janua mints
for Fashion Cabinet was decorative server-side. Ruled 2026-08-25.

### Semantics

| Caller | `log` mode (default) | `enforce` mode |
|---|---|---|
| Anonymous (no token) | **unchanged** — guest tier, rate-limited | **unchanged** |
| Human token | **unchanged** — `yantra4d_tier` as today | **unchanged** |
| Machine token **with** `yantra4d:render` | **unchanged** — `yantra4d_tier` as today | **unchanged** |
| Machine token **without** the scope | structured warning, request **allowed** | **403** `missing_scope` |

Only the last row ever changes behaviour. Anonymous and human access to the render
routes stays exactly tier/rate-limit driven; a conformant machine token resolves its
tier through the same `resolve_tier` path as before.

Detection keys on the union of `token_use == "client_credentials"`,
`actor_type == "service_account"`, and a `service-account:` prefixed `sub`. Any one
suffices, so a partial claim set fails toward *machine* rather than slipping through
the human path. Human tokens carry none of these markers.

### Observation window

In `log` mode, a non-conformant machine token emits one warning per request on the
`middleware.auth` logger:

```
render.scope_missing client_id=<id> missing_scope=yantra4d:render \
  present_scopes=<a,b> path=/api/render mode=log outcome=allowed
```

The token itself is never logged. Grep `render.scope_missing` to enumerate which
clients would break before flipping the switch.

### Flip playbook

Mirrors the `RENDER_STRICT_PAYLOAD` rollout: ship in `log`, observe, then enforce.

1. Deploy with `RENDER_SCOPE_ENFORCEMENT` unset (defaults to `log`).
2. Watch `render.scope_missing` for a quiet observation window — a full billing
   cycle of machine traffic is the safe minimum, since some service clients run on
   monthly cadences.
3. For each `client_id` that appears, add the `yantra4d:render` scope to that OAuth
   client in Janua and have the consumer re-mint. Service tokens live one hour, so
   a re-mint propagates within the hour with no redeploy.
4. When the window is quiet, set `RENDER_SCOPE_ENFORCEMENT=enforce`.
5. Rollback is a single env flip back to `log` — no code change, no redeploy of
   consumers.

Fashion Cabinet is already conformant: `fashion-cabinet/apps/api/body_render.py`
mints with `scope=yantra4d:render` against `aud=yantra4d-api`, so it passes in both
modes. This is pinned by a test using FC's exact token shape.

---

## Configuration

Auth settings are defined in `apps/api/config.py`.

| Variable | Default | Description |
|----------|---------|-------------|
| `JANUA_ISSUER` | `https://auth.madfam.io` | The JWT `iss` claim value and base URL for JWKS discovery. |
| `JANUA_AUDIENCE` | `yantra4d-api` | The expected JWT `aud` claim. Must match the audience registered in the Janua seed script. |
| `AUTH_ENABLED` | `true` | Set to `false` to disable all auth checks for local development. |
| `RENDER_SCOPE_ENFORCEMENT` | `log` | `log` warns and allows machine tokens missing `yantra4d:render`; `enforce` returns 403. Read from the environment at call time, not via `Config`. See [Machine tokens and render scope](#machine-tokens-and-render-scope). |
| `TIER_OVERRIDES` | unset | JSON object mapping a lower-cased `email` claim to a tier name (`guest`/`essentials`/`pro`/`madfam`). Authoritative for that identity: it can raise or lower the tier the `yantra4d_tier` claim would give. Read at call time. Lives in a Secret in production; never in this repo. |
| `PRIVATE_PROJECTS` | unset | Comma-separated project slugs forced private regardless of their manifest (fail-closed for client cartridges). |
| `PROJECT_ACCESS_GRANTS` | unset | JSON object `{ "<slug>": ["<email>", …] }` granting private-project access to specific identities. Read at call time. Lives in a Secret in production. |

When `AUTH_ENABLED` is `false`, all decorators become no-ops. The request context will not contain auth payload data.

---

## JWKS Caching

Token validation uses `PyJWKClient` to fetch signing keys from `{JANUA_ISSUER}/.well-known/jwks.json`.

- **Cache lifespan**: 1 hour.
- **Initialization**: Lazy. The JWKS client is created on the first request that requires authentication, not at application startup.
- **Failure behavior**: If a JWKS fetch fails after the cache has expired, the request fails with a 500 error. There is no stale-while-revalidate fallback.

---

## Audience

The audience claim `yantra4d-api` is aligned with the Janua seed script that pre-registers the OAuth client. This value must be consistent across three locations:

1. The `JANUA_AUDIENCE` environment variable in the Yantra4D API.
2. The audience field in the Janua OAuth client registration.
3. The audience parameter requested during the OAuth flow.

A mismatch in any of these causes token validation to fail with a 401 error.

---

## Private projects and identity tier overrides

Two related mechanisms, both configured through the environment so that the
public repository never carries an identity.

### Identity tier overrides

`resolve_tier()` is the single funnel from JWT claims to a tier. When
`TIER_OVERRIDES` names the caller's lower-cased `email` claim, that mapping wins
over the `yantra4d_tier` claim — in both directions. It exists so staff can hold
the top tier without waiting on the Janua-side entitlement push (gate `[Y1]`),
and so an identity can be pinned down as well as up. `/api/me` reports the
source as `tier_override` so the diagnostic stays honest.

The top tier, `madfam`, is **unlimited** for `backend_renders_per_hour` and
`ai_requests_per_hour`: `tiers.json` uses `-1` as the sentinel (the same one
`max_projects` already used), the rate-limiter exempts those requests instead of
being handed a `-1/hour` string, and the render response carries
`X-RateLimit-Limit: unlimited` with no `Remaining`/`Reset`.

### Private projects

A project is private when its slug is listed in `PRIVATE_PROJECTS` **or** its
manifest declares `access_control.view: "private"` (the schema's `access_control`
enum gained the value `private`; the env list is the fail-closed backstop for
client cartridges whose manifests live in other repositories).

A private project is visible to a caller when any of these hold:

- the caller resolves to the `madfam` tier (including via `TIER_OVERRIDES`);
- the caller's claims carry the `admin` role;
- the caller's lower-cased `email` is listed for that slug in `PROJECT_ACCESS_GRANTS`.

Everyone else — anonymous or signed in — receives **HTTP 403** with
`error_code: "project_locked"` and `auth_required: true|false` (true when the
caller is anonymous), from every surface that could leak the cartridge: the
project list (the project is simply absent), manifest, meta and parts, render /
render-stream / render-cancel, download and export, verify, storefront and share
links, BOM / datasheet / assembly / animations / cart, the editor routes, and the
`/static/<slug>_preview_*` render artifacts (whose names are otherwise
predictable). Private manifests are served with `Cache-Control: private,
no-store`. `unlisted` is unchanged and orthogonal.

Not gated in this change: the render **WebSocket** progress channel (it relays
job progress for a job the API already authorized) and the admin-only
`/api/admin/projects/tablaco/public-link` (it returns a URL; the URL itself now
lands on the locked screen for anyone without access).

### Operator playbook

1. Put the identities in the `yantra4d-secrets` Secret via Enclii (never in a
   manifest):
   - `TIER_OVERRIDES` — e.g. `{"person@example.com":"madfam"}`
   - `PROJECT_ACCESS_GRANTS` — e.g. `{"tablaco":["client@example.com"]}` (only
     needed for identities that must see a private project **without** the
     `madfam` tier)
2. Confirm `PRIVATE_PROJECTS` in `k8s/production/yantra4d-backend-deployment.yaml`
   lists every client cartridge the backend image carries (the image build
   initialises them explicitly in `deploy.yml › build-backend`).
3. Roll the backend (a new digest pin or `kubectl rollout restart` through
   Enclii) so the pod reads the new keys — they are read at call time, but the
   Secret is mounted at pod start.
4. Verify without touching a secret: `curl -s -o /dev/null -w '%{http_code}'
   https://api.yantra4d.com/api/projects/tablaco/manifest` → `403` anonymously;
   the same request with an authorized bearer → `200`; the Studio at
   `/project/tablaco` shows the locked screen anonymously and renders after an
   authorized sign-in.

## Future Work

**JIT User Provisioning (P2)**: Currently, Yantra4D does not create local user records when a user authenticates for the first time. The `sub` claim from the JWT is used directly as the user identifier. A future iteration will provision local user records on first login to support user preferences, project ownership, and usage tracking.

---

## Troubleshooting

### 401 Unauthorized on all requests

**Possible causes**:

- **Audience mismatch**: The `aud` claim in the token does not match `JANUA_AUDIENCE`. Verify the OAuth client in Janua is registered with audience `yantra4d-api`.
- **Issuer mismatch**: The `iss` claim does not match `JANUA_ISSUER`. Check that both the Janua instance and the config point to the same URL.
- **Expired token**: The access token has expired. The client must refresh it.

### 403 Forbidden despite valid authentication

**Cause**: The user's token does not contain the required role or tier claim.

**Fix**:
- Check the user's role assignment in Janua.
- Verify the token includes the expected custom claims (`role`, `tier`).
- Use a JWT decoder (e.g., `jwt.io`) to inspect the token payload.

### 500 Internal Server Error on first request

**Cause**: JWKS fetch failed. The application cannot reach the Janua issuer URL.

**Fix**:
- Verify network connectivity to the Janua instance.
- Check that `JANUA_ISSUER` is set correctly.
- If running locally, ensure Janua is running and accessible.

### Auth checks active in local development

**Symptom**: Routes require authentication when developing locally without Janua running.

**Fix**: Set `AUTH_ENABLED=false` in your environment and restart the Flask application.

### Token missing role or tier claims

**Symptom**: `@require_role` or `@require_tier` returns 403 even for users who should have access.

**Cause**: The Janua OAuth client may not be configured to include custom claims in the token.

**Fix**: Verify the OAuth client configuration in Janua includes the `role` and `tier` claims in the token scope or custom claims mapping.
