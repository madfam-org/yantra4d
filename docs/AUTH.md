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

---

## Configuration

Auth settings are defined in `apps/api/config.py`.

| Variable | Default | Description |
|----------|---------|-------------|
| `JANUA_ISSUER` | `https://auth.madfam.io` | The JWT `iss` claim value and base URL for JWKS discovery. |
| `JANUA_AUDIENCE` | `yantra4d-api` | The expected JWT `aud` claim. Must match the audience registered in the Janua seed script. |
| `AUTH_ENABLED` | `true` | Set to `false` to disable all auth checks for local development. |

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
