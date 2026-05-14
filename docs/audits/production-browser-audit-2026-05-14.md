# Production Browser Audit - 2026-05-14

## Scope

Live browser and API audit of:

- `https://yantra4d.com`
- `https://app.yantra4d.com`
- `https://admin.yantra4d.com`
- `https://api.yantra4d.com`
- private Tablaco Studio route: `https://app.yantra4d.com/project/tablaco`

## Findings

1. Landing, Studio shell, and Admin shell loaded over HTTPS with no page errors.
2. Tablaco manifest was available at `/api/projects/tablaco/manifest` even though Tablaco is intentionally unlisted from `/api/projects`.
3. Tablaco browser render initially failed because `/api/render-stream` returned Cloudflare `502`; the browser surfaced it as a CORS failure because upstream 502 responses did not include app-origin CORS headers.
4. `yantra4d-backend` was unhealthy: backend pods had `0` ready replicas.
5. The render-worker sidecar failed with `ModuleNotFoundError: No module named 'config'` because the worker process did not have `/app/backend` on `PYTHONPATH`.
6. The previous worker image also failed with `python: can't open file '/app/worker/render_worker.py'` before the newest image was active.
7. Backend rolling update deadlocked on the RWO `yantra4d-analytics` PVC; the replacement pod hit `Multi-Attach` and later Longhorn reported the volume as `faulted`/`detaching`.
8. A fresh ephemeral SQLite data dir exposed migration `002` using `op.create_unique_constraint`, which SQLite cannot apply outside batch mode.

## Remediation Applied

- Recovered production backend by clearing the failed rollout deadlock.
- Replaced the live analytics PVC mount with `emptyDir` to restore API availability while avoiding the faulted RWO volume.
- Set `PYTHONPATH=/app/backend` for the live render-worker sidecar.
- Cancelled stale render jobs via `/api/render-cancel`.
- Updated durable manifests/code:
  - SQLite-safe migration `002`.
  - Worker import path bootstrap.
  - Production `Recreate` rollout strategy.
  - Production `emptyDir` analytics data mount.
  - Render-worker readiness probe.
  - Docker Compose worker `PYTHONPATH`.

## Enclii Adapter Gaps

Raw Kubernetes access was used only as break-glass after these Enclii gaps:

- `enclii ops pods diagnose --project yantra4d --service yantra4d-backend` returned zero pods while Enclii health showed the backend unhealthy.
- `enclii logs yantra4d-backend --env production` could resolve the service ID but failed because no deployment metadata was available.
- `enclii ops pods logs --project yantra4d --service yantra4d-backend` required a pod target and could not map service to pods.
- `enclii ops storage pvc --project yantra4d --service yantra4d-backend` returned zero PVCs.
- `enclii ops storage repair-plan ...` produced a dry-run plan but reported apply execution was not wired.

These should be implemented before raw pod/storage operations can be removed from incident response.
