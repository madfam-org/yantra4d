---
title: API Quickstart
description: Getting started with the Yantra4D REST API — health checks, project listing, manifests, rendering, and exports.
---

The Yantra4D API is a Flask application that handles rendering, project management, export, and AI features. This guide covers the most common API operations with `curl` examples.

**Base URL:** `https://api.yantra4d.com` (production) or `http://localhost:5000` (local development)

## Health check

Verify the API is running and OpenSCAD is available:

```bash
curl https://api.yantra4d.com/api/health
```

Response:

```json
{
  "status": "healthy",
  "openscad": "available",
  "version": "1.0.0"
}
```

## List projects

Retrieve all available projects:

```bash
curl https://api.yantra4d.com/api/projects
```

Response:

```json
[
  {
    "slug": "gridfinity",
    "name": "Gridfinity Extended",
    "thumbnail": "/projects/gridfinity.webp",
    "tags": ["storage", "modular", "organization"],
    "difficulty": "beginner"
  },
  {
    "slug": "microscope-slide-holder",
    "name": "Microscope Slide Holder",
    "tags": ["lab", "science", "hyperobject"],
    "difficulty": "intermediate"
  }
]
```

Add `?stats=1` to include 30-day analytics counts per project.

## Fetch a project manifest

The manifest is the single source of truth for a project's modes, parameters, parts, and configuration:

```bash
curl https://api.yantra4d.com/api/projects/gridfinity/manifest
```

Response (abbreviated):

```json
{
  "project": {
    "name": "Gridfinity Extended",
    "slug": "gridfinity"
  },
  "modes": [
    {
      "id": "unit",
      "scad_file": "half_cube.scad",
      "label": { "en": "Unit", "es": "Unidad" },
      "parts": ["main"]
    }
  ],
  "parameters": [
    {
      "id": "width_units",
      "type": "slider",
      "default": 2,
      "min": 1,
      "max": 10,
      "step": 1,
      "label": { "en": "Width (units)" }
    }
  ]
}
```

The manifest supports ETags for conditional requests. The API returns `304 Not Modified` if the manifest has not changed.

## Render a model

Trigger a synchronous render and receive the output file:

```bash
curl -X POST https://api.yantra4d.com/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "project": "gridfinity",
    "mode": "unit",
    "parameters": {
      "width_units": 3,
      "depth_units": 2,
      "height_units": 6
    },
    "parts": ["main"]
  }' \
  --output model.glb
```

The response body is the rendered file. STL renders are automatically converted to GLB for web delivery. To get a specific format, add `export_format`:

```bash
curl -X POST https://api.yantra4d.com/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "project": "gridfinity",
    "mode": "unit",
    "parameters": { "width_units": 2 },
    "parts": ["main"],
    "export_format": "step"
  }' \
  --output model.step
```

Available `export_format` values depend on the project's engine and tier access: `stl`, `3mf`, `off`, `step`, `glb`, `gltf`, `obj`.

### Streaming render

For long-running renders, use the SSE streaming endpoint:

```bash
curl -X POST https://api.yantra4d.com/api/render-stream \
  -H "Content-Type: application/json" \
  -d '{
    "project": "gridfinity",
    "mode": "unit",
    "parameters": { "width_units": 2 },
    "parts": ["main"]
  }'
```

The response is a Server-Sent Events stream with progress updates.

## Estimate render time

Before rendering, you can estimate how long it will take:

```bash
curl -X POST https://api.yantra4d.com/api/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "project": "gridfinity",
    "mode": "unit",
    "parameters": { "width_units": 4, "depth_units": 4 }
  }'
```

Response:

```json
{
  "estimated_seconds": 45,
  "num_units": 16,
  "num_parts": 1,
  "show_warning": false
}
```

## Download files

Download rendered or source artifacts directly:

```bash
# Download any supported artifact format
curl https://api.yantra4d.com/api/projects/gridfinity/download/3mf/main.3mf \
  --output main.3mf

# Download legacy STL route
curl https://api.yantra4d.com/api/projects/gridfinity/download/stl/main.stl \
  --output main.stl

# Download a SCAD source file
curl https://api.yantra4d.com/api/projects/gridfinity/download/scad/half_cube.scad \
  --output half_cube.scad
```

Supported file formats: `stl`, `scad`, `3mf`, `obj`, `off`, `step`, `glb`, `gltf`.

## Bill of Materials

Retrieve the hardware BOM for a project:

```bash
# JSON format
curl "https://api.yantra4d.com/api/projects/gridfinity/bom?width_units=3&depth_units=2"

# CSV format
curl "https://api.yantra4d.com/api/projects/gridfinity/bom?format=csv&width_units=3"
```

BOM quantities are computed from formulas that reference parameter values. Changing parameters changes the quantities.

## Authentication

Most read endpoints work without authentication. Write operations and tier-gated features require a JWT bearer token:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://api.yantra4d.com/api/projects/my-project/files
```

For local development, set `AUTH_ENABLED=false` in your environment to bypass authentication. All requests will receive full (madfam tier) access.

## Rate limits

Endpoints are rate-limited per tier. Rate limit headers are included in responses:

```
X-RateLimit-Limit: 200
X-RateLimit-Tier: pro
```

| Endpoint | Default limit |
|----------|:---:|
| Render | Tier-based (30-500/hr) |
| Estimate | 200/hr |
| Verify | 50/hr |

## Error responses

All errors follow a consistent format:

```json
{
  "error": "Description of what went wrong"
}
```

Common HTTP status codes:

| Code | Meaning |
|------|---------|
| 400 | Invalid request (missing parameters, unsupported format) |
| 404 | Project or resource not found |
| 429 | Rate limit exceeded |
| 503 | Service unavailable (OpenSCAD not found, AI not configured) |

## Next steps

- [Creating Projects](/developer/creating-projects/) -- onboard your own SCAD projects
- [Manifest Specs](/commons/manifest-specs/) -- full manifest schema reference
- [AI Features](/platform/ai-assistant/) -- AI Configurator and Code Editor APIs
