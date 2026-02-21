---
title: Core APIs
description: Backend Node API references
---

The Yantra4D API executes inside a high-performance Flask/Node array.

## Express Endpoints

### `POST /api/v1/generate`
Passes JSON representations of `project.json` defaults and user-modified parameters, streaming the `.stl` or `.step` output synchronously back.
- Uses `shm_size: 2gb` in containerization to compute massive artifacts.

### `GET /api/v1/library/commons/:id`
Retrieves the open-source JSON manifest data directly from the system storage disk.

## Terminal Executables
A suite of internal scripts handle Yantra4D's testing suite:
- `validate_manifests.py`: Strictly ensures all 35+ hyperobjects conform to internal schemas.
- `apps/studio/package.json` testing targets native React Vite integrations for regression checking.
