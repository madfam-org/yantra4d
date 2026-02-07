# Yantra4D Production Verification Prompt

Run this after deploying Yantra4D to the `enclii-production` namespace to verify all three services are online, healthy, and correctly integrated.

---

## Service Map

| Service | Domain | Internal Port | Health Path |
|---------|--------|---------------|-------------|
| Landing | `4d.madfam.io` | 80 | `/` (200 + HTML) |
| API | `4d-api.madfam.io` | 5000 | `/api/health` (200 + JSON) |
| Studio | `4d-app.madfam.io` | 80 | `/` (200 + HTML) |

---

## Verification Steps

### 1. DNS Resolution

Verify all three domains resolve via Cloudflare Tunnel CNAME:

```bash
dig 4d.madfam.io CNAME +short
dig 4d-api.madfam.io CNAME +short
dig 4d-app.madfam.io CNAME +short
```

**Expected**: Each returns a `*.cfargotunnel.com` or `tunnel.enclii.dev` CNAME.
**Fail criteria**: NXDOMAIN or no CNAME record.

---

### 2. TLS Certificate Validity

```bash
echo | openssl s_client -servername 4d.madfam.io -connect 4d.madfam.io:443 2>/dev/null | openssl x509 -noout -dates -subject
echo | openssl s_client -servername 4d-api.madfam.io -connect 4d-api.madfam.io:443 2>/dev/null | openssl x509 -noout -dates -subject
echo | openssl s_client -servername 4d-app.madfam.io -connect 4d-app.madfam.io:443 2>/dev/null | openssl x509 -noout -dates -subject
```

**Expected**: Valid cert covering each domain, `notAfter` in the future.
**Fail criteria**: Expired cert, wrong CN/SAN, self-signed.

---

### 3. API Health Check

```bash
curl -sS -o /dev/null -w '%{http_code}' https://4d-api.madfam.io/api/health
curl -sS https://4d-api.madfam.io/api/health | python3 -m json.tool
```

**Expected response**:
```json
{
    "status": "healthy",
    "openscad_available": true,
    "debug_mode": false
}
```

**Fail criteria**: Non-200 status, `openscad_available: false`, `debug_mode: true`, connection refused.

---

### 4. API Functional Smoke Test

#### 4a. Project listing
```bash
curl -sS https://4d-api.madfam.io/api/projects | python3 -m json.tool | head -20
```
**Expected**: JSON array with 20 project entries (slugs like `tablaco`, `gridfinity`, `voronoi`, etc.).

#### 4b. Single project manifest
```bash
curl -sS https://4d-api.madfam.io/api/projects/tablaco/manifest | python3 -m json.tool | head -5
```
**Expected**: 200 with JSON containing `name`, `modes`, `parameters` keys.

---

### 5. Studio Serves SPA

```bash
curl -sS -o /dev/null -w '%{http_code}' https://4d-app.madfam.io
curl -sS https://4d-app.madfam.io | head -5
```

**Expected**: 200 with `<!doctype html>` (Vite SPA shell). Non-root paths like `/nonexistent` should also return 200 (SPA fallback).

```bash
curl -sS -o /dev/null -w '%{http_code}' https://4d-app.madfam.io/nonexistent
```

**Expected**: 200 (nginx `try_files` → `/index.html`).

---

### 6. Landing Page Serves HTML

```bash
curl -sS -o /dev/null -w '%{http_code}' https://4d.madfam.io
curl -sS https://4d.madfam.io | grep -o '<title>[^<]*</title>'
```

**Expected**: 200, `<title>` contains "Yantra4D".

---

### 7. Security Headers

#### 7a. Studio CSP
```bash
curl -sI https://4d-app.madfam.io | grep -i content-security-policy
```

**Expected CSP must contain**:
- `connect-src 'self' https://4d-api.madfam.io https://auth.madfam.io blob:`
- `frame-ancestors 'self' https://4d.madfam.io`
- `wasm-unsafe-eval` in `script-src` (required for OpenSCAD WASM)

#### 7b. Landing CSP
```bash
curl -sI https://4d.madfam.io | grep -i content-security-policy
```

**Expected CSP must contain**:
- `frame-src https://4d-app.madfam.io`
- `connect-src 'self' https://4d-api.madfam.io`

#### 7c. Common security headers (all 3 services)
```bash
for domain in 4d.madfam.io 4d-api.madfam.io 4d-app.madfam.io; do
  echo "=== $domain ==="
  curl -sI "https://$domain" | grep -iE 'x-content-type|x-frame-options|referrer-policy'
done
```

**Expected** (each service):
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Referrer-Policy: strict-origin-when-cross-origin`

---

### 8. CORS Validation

```bash
curl -sI -H "Origin: https://4d-app.madfam.io" https://4d-api.madfam.io/api/health | grep -i access-control
```

**Expected**: `Access-Control-Allow-Origin: https://4d-app.madfam.io`

```bash
curl -sI -H "Origin: https://evil.com" https://4d-api.madfam.io/api/health | grep -i access-control
```

**Expected**: No `Access-Control-Allow-Origin` header (origin rejected).

**Note**: The backend `CORS_ORIGINS` env var must be set to `https://4d.madfam.io,https://4d-app.madfam.io` in the K8s deployment.

---

### 9. Janua Auth Integration

#### 9a. JWKS endpoint reachable from API
```bash
curl -sS https://auth.madfam.io/.well-known/jwks.json | python3 -m json.tool | head -5
```

**Expected**: JSON with `keys` array containing at least one RSA/EC key.

#### 9b. Unauthenticated API access (tier-gated endpoints)
```bash
curl -sS -o /dev/null -w '%{http_code}' https://4d-api.madfam.io/api/projects/tablaco/git/status
```

**Expected**: 401 (requires valid JWT).

#### 9c. Studio OAuth redirect
```bash
curl -sS https://4d-app.madfam.io | grep -o 'VITE_JANUA_BASE_URL[^"]*"[^"]*"'
```

**Expected**: Embedded env var pointing to `https://auth.madfam.io`.

---

### 10. Cross-Service Connectivity

#### 10a. Landing embeds Studio (iframe)
```bash
curl -sS https://4d.madfam.io | grep -o '4d-app\.madfam\.io'
```

**Expected**: At least one match (InteractiveShowcase iframe src or link href).

#### 10b. Studio connects to API
```bash
curl -sS https://4d-app.madfam.io | grep -o '4d-api\.madfam\.io'
```

**Expected**: At least one match (VITE_API_BASE baked into JS bundle).

---

### 11. K8s Pod Health

```bash
kubectl get pods -n enclii-production -l 'app in (yantra4d-backend,yantra4d-studio,yantra4d-landing)' -o wide
```

**Expected**: All pods in `Running` state, `READY` column shows `1/1` (or `2/2` etc.), no restarts.

```bash
kubectl get deployments -n enclii-production | grep yantra4d
```

**Expected**: `READY` matches `DESIRED` for all three deployments.

---

### 12. GHCR Images

```bash
kubectl get deployments -n enclii-production -o jsonpath='{range .items[?(@.metadata.name=="yantra4d-backend")]}{.spec.template.spec.containers[0].image}{end}'
kubectl get deployments -n enclii-production -o jsonpath='{range .items[?(@.metadata.name=="yantra4d-studio")]}{.spec.template.spec.containers[0].image}{end}'
kubectl get deployments -n enclii-production -o jsonpath='{range .items[?(@.metadata.name=="yantra4d-landing")]}{.spec.template.spec.containers[0].image}{end}'
```

**Expected**: Images from `ghcr.io/madfam-org/yantra4d/{backend,studio,landing}` with SHA digest or `:main` tag.

---

## Pass/Fail Summary Template

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | DNS Resolution (3 domains) | | |
| 2 | TLS Certificates | | |
| 3 | API Health (`/api/health`) | | |
| 4 | API Smoke (projects + manifest) | | |
| 5 | Studio SPA Serving | | |
| 6 | Landing HTML Serving | | |
| 7 | Security Headers (CSP + common) | | |
| 8 | CORS (allow studio, reject evil) | | |
| 9 | Janua Auth (JWKS + 401 + redirect) | | |
| 10 | Cross-Service Links | | |
| 11 | K8s Pod Health | | |
| 12 | GHCR Image Tags | | |

**Overall**: PASS if all 12 checks pass. Any FAIL blocks production sign-off.
