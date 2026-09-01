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

## Identity tier overrides

`resolve_tier()` (`apps/api/services/core/tier_service.py`) is the single funnel
every tier decision goes through, so the override lives there rather than at
each call site.

`TIER_OVERRIDES` is a JSON object mapping a **lower-cased email address** to a
tier name:

```json
{"someone@example.com": "madfam"}
```

- Read from the environment at call time (like `RENDER_SCOPE_ENFORCEMENT`), and
  parsed at most once per distinct value — rolling the secret needs no restart.
- Unset, empty, non-JSON, or a non-object value all mean *no overrides*, with a
  warning. A broken map never takes the API down and never grants anything.
- Entries naming an unknown tier are dropped with a warning.
- An override is **authoritative**: it applies whether it raises a tier (a staff
  identity to `madfam`) or lowers one, and it beats the token's `yantra4d_tier`.
- Email addresses are identities: they are counted in logs, never printed above
  `DEBUG`.

`/api/me` reports `entitlement.source = "tier_override"` when one applied, so a
tier that the token does not carry is never unexplained.

The override map is deployment configuration (a Kubernetes secret). No identity
is ever committed to this repository.

---

## Private projects

A project is *private* when it must render only for identities entitled to it.
Everything else gets one machine-readable refusal:

```http
HTTP/1.1 403 Forbidden
```
```json
{
  "status": "error",
  "error": "This project is private",
  "error_code": "project_locked",
  "auth_required": true,
  "request_id": "…"
}
```

`auth_required` tells the Studio which call to action to show: `true` means
nobody is signed in (offer sign-in), `false` means the caller is signed in and
still not entitled (offer request-access).

### Declaring privacy

| Source | Shape | Notes |
|---|---|---|
| Manifest | `access_control.view: "private"` | The cartridge's own statement; travels with the project. |
| `PRIVATE_PROJECTS` | `"acme-bracket,client-widget"` | Comma-separated slugs forced private **regardless of the manifest**. Fail-closed defence for client cartridges: a regenerated or submodule-bumped manifest cannot re-open them. |

`unlisted` is unchanged and independent: it hides a public project from the
index, privacy withholds the project itself.

### Who may view a private project

Checked in order by `can_view_project()`
(`apps/api/services/core/project_access.py`):

1. the top tier — `resolve_tier(claims) == "madfam"`, which includes anyone
   seated there by `TIER_OVERRIDES`;
2. the `admin` role on the token;
3. `PROJECT_ACCESS_GRANTS`, a JSON object mapping slug to allowed emails:
   `{"acme-bracket": ["someone@example.com"]}`.

Anonymous callers never qualify — there is no identity to check.

### What is gated

Project listing (private entries are dropped before the `unlisted` filter),
manifest, meta, parts, storefront and share, downloads and exports, render /
render-stream / render-cancel, verify, bom / datasheet / assembly / animations /
cart, fork, editor and git routes, analysis, simulation, the Cotiza export, the
analytics summary, and `/static/<slug>_preview_*` render artifacts.

Responses that depend on who is asking are never shared-cached: the private
manifest is served `private, no-store` with no ETag, and the project list drops
to `private, no-store` as soon as any project in it is private.

Both env vars are read at call time and both are deployment configuration (a
Kubernetes secret). No identity is ever committed to this repository.

---

## Configuration

Auth settings are defined in `apps/api/config.py`.

| Variable | Default | Description |
|----------|---------|-------------|
| `JANUA_ISSUER` | `https://auth.madfam.io` | The JWT `iss` claim value and base URL for JWKS discovery. |
| `JANUA_AUDIENCE` | `yantra4d-api` | The expected JWT `aud` claim. Must match the audience registered in the Janua seed script. |
| `AUTH_ENABLED` | `true` | Set to `false` to disable all auth checks for local development. |
| `RENDER_SCOPE_ENFORCEMENT` | `log` | `log` warns and allows machine tokens missing `yantra4d:render`; `enforce` returns 403. Read from the environment at call time, not via `Config`. See [Machine tokens and render scope](#machine-tokens-and-render-scope). |
| `TIER_OVERRIDES` | *(unset)* | JSON object mapping lower-cased email to tier name, e.g. `{"someone@example.com": "madfam"}`. Authoritative — raises or lowers the tier the token claims. Read at call time, not via `Config`. See [Identity tier overrides](#identity-tier-overrides). |
| `PRIVATE_PROJECTS` | *(unset)* | Comma-separated slugs forced private regardless of their manifest. Read at call time. See [Private projects](#private-projects). |
| `PROJECT_ACCESS_GRANTS` | *(unset)* | JSON object mapping slug to a list of emails granted access to that private project, e.g. `{"acme-bracket": ["someone@example.com"]}`. Read at call time. |

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
