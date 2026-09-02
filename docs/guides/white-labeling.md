# White-Labeling Guide

> [!IMPORTANT]
> MADFAM-ENCLII-FIRST-LEGACY-RAW v1: This document contains legacy raw infrastructure command examples.
> Routine production operations must use Enclii web, API, or CLI. Treat raw
> `kubectl`, `helm`, SSH, provider CLI/API, `docker exec`, and direct container
> access as platform bootstrap or documented break-glass only, and record any
> missing Enclii adapter gap.


This guide explains how to deploy a fully white-labeled instance of Yantra4D
under your own brand, domain, and identity.

---

## Overview

Yantra4D supports white-labeling via three environment variables that replace
the platform's name, logo, and branding at runtime — **without any code changes**.
The platform name and logo are served dynamically through the
`GET /api/config/client` endpoint and injected into the Studio via the
`PlatformProvider` React context.

White-label branding is gated behind a valid **license key** at `pro` tier or
above. Without a valid key, the platform falls back to `"Yantra4D"` branding.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `YANTRA4D_LICENSE_KEY` | Yes | A JWT issued by `auth.madfam.io` identifying your `pro` or `premium` tier account (the deprecated `madfam` tier name is still accepted) |
| `PLATFORM_NAME` | Yes | The brand name displayed in the Studio header and browser tab title |
| `PLATFORM_LOGO` | Yes | URL or path to your logo image (served at this path by your web server) |

---

## How It Works

```
Browser (React Studio)
    │
    ▼
GET /api/config/client
    │
    ▼ client_config.py
    ├─ Reads YANTRA4D_LICENSE_KEY from env
    ├─ Decodes JWT via Janua JWKS (auth.madfam.io)
    ├─ Resolves tier from claims
    ├─ If tier >= pro: responds with PLATFORM_NAME + PLATFORM_LOGO
    └─ Otherwise: responds with "Yantra4D" + "/logo.png"
    │
    ▼
PlatformProvider (contexts/system/PlatformProvider.jsx)
    │   Caches platformName + platformLogo in React context
    ▼
StudioHeader / ProjectsView
    └─ Renders brand name + logo from context
```

> **Note on license key enforcement:** The `YANTRA4D_LICENSE_KEY` is verified
> as a JWT using the Janua JWKS endpoint and must belong to a `pro` or `premium`
> tier account (a licence minted before the `madfam` → `premium` rename still
> validates — the old name is a permanent alias). The verification checks signature, expiry, and audience
> (`yantra4d-api`). Expired or revoked tokens fall back to default branding
> transparently.

---

## Quickstart: Docker Compose Override

Create a `docker-compose.override.yml` alongside your `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - PLATFORM_NAME=AcmeParts Studio
      - PLATFORM_LOGO=/acme-logo.png
      - YANTRA4D_LICENSE_KEY=eyJhbGciO...  # your JWT

  studio:
    volumes:
      # Serve your logo through the nginx container
      - ./branding/acme-logo.png:/usr/share/nginx/html/acme-logo.png:ro
```

Then start the stack:

```bash
docker compose up --build
```

The Studio at `http://localhost:3000` will reflect your brand immediately.

---

## Production Deployment (Enclii)

### 1. Create the Secret holding the license key

Create it through **Enclii's secrets intake** — the Enclii console, API, or CLI
— on the `yantra4d-backend` service. Do not reach past Enclii to the cluster to
create it by hand; if the secrets intake cannot express something this needs,
record the Enclii adapter gap instead of routing around it.

The shape Enclii creates and projects:

| | |
| :-- | :-- |
| Secret name | `yantra4d-license` |
| Key | `YANTRA4D_LICENSE_KEY` |
| Value | the raw license JWT (`eyJhbGciO…`) |
| Consumed by | the `yantra4d-backend` service only — the Studio never sees it |

Redeploy or restart the backend afterwards so the new environment is picked up.

### 2. Create a ConfigMap for brand settings

```yaml
# k8s/production/brand-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: yantra4d-brand
data:
  PLATFORM_NAME: "AcmeParts Studio"
  PLATFORM_LOGO: "https://cdn.acme.com/logo.png"
```

### 3. Reference both from the backend

The backend reads its environment from the brand ConfigMap and the license
Secret together:

```yaml
envFrom:
  - configMapRef:
      name: yantra4d-brand
  - secretRef:
      name: yantra4d-license
```

Enclii wires this projection for the `yantra4d-backend` service; the manifest
above is shown so you can recognise the resulting shape, not as a step to apply
by hand.

---

## Custom Domain & CORS

To serve the platform on your own domain (e.g., `studio.acme.com`), update
`CORS_ORIGINS` on the backend to include your domain:

```yaml
environment:
  - CORS_ORIGINS=https://studio.acme.com,https://acme.com
```

Configure your DNS and TLS termination (via Ingress or Cloudflare) to point
`studio.acme.com` at your Studio service.

---

## Logo Requirements

- **Format:** PNG, SVG, or WebP recommended
- **Dimensions:** Height `24–32px` rendered in the Studio header; provide at
  least `64px` tall source image for HiDPI displays
- **Background:** Transparent background recommended; the header is themed
  (light/dark) so opaque backgrounds may clash
- **Serving:** The logo URL in `PLATFORM_LOGO` must be reachable from the
  browser. Use an absolute URL (CDN) or include the file in your nginx/Studio
  container's `public/` directory

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Studio shows "Yantra4D" instead of your brand | License key invalid, expired, or tier too low | Verify `YANTRA4D_LICENSE_KEY` is a valid JWT with `pro`+ tier; check backend logs for `License key JWT validation failed` |
| Logo shows as broken image | `PLATFORM_LOGO` URL unreachable from browser | Use an absolute CDN URL, or verify the file is mounted in the Studio nginx container |
| CORS error on `GET /api/config/client` | Studio domain not in `CORS_ORIGINS` | Add your domain to the backend `CORS_ORIGINS` env var |
| Changes not reflected after redeployment | Browser cached old `/api/config/client` response | Hard refresh (Cmd/Ctrl+Shift+R) or clear browser cache |
