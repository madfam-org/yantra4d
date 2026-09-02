# Render worker capacity — dedicated Deployment, HPA, PDBs

**Status:** manifests written, **not applied**. Everything here is applied by
the operator through Enclii/ArgoCD. Nothing in this change was run against the
cluster, and no `kubectl` was used to produce it.

This page describes the topology change, the prerequisite that gates it, the
rollout order, rollback, and what `/api/health` reports afterwards.

---

## What changes

The render worker was a **sidecar in the `yantra4d-backend` pod**. That tied
render capacity to API capacity: the only way to get a second worker was a
second API replica, and the API is a singleton — `strategy: Recreate` and a
ReadWriteOnce analytics PVC both hold it at one. Every render goes through the
worker (`render_orchestrator` refuses to render inline and returns "Render
worker unavailable or not healthy" when no heartbeat is fresh), so one worker
was the platform's hard render ceiling.

After this change:

| | Before | After |
|---|---|---|
| Worker location | sidecar in the API pod | `yantra4d-render-worker` Deployment |
| Worker replicas | 1, fixed to the API | 1→4, HPA on CPU |
| Worker requests / limits | 100m / 256Mi → 1000m / 2Gi | 500m / 512Mi → 1000m / 2Gi |
| Render output volume | `emptyDir`, shared inside the pod | `yantra4d-render-output` **RWX PVC**, shared across pods |
| Worker heartbeat | one fleet-wide Redis key | one key per pod, `render_worker:heartbeat:<pod-name>` |
| Worker probes | readiness only, on the shared key | readiness **and** liveness, on the pod's own key |
| Disruption budget | none | one for the API, one for the worker |
| API replicas | 1 | 1 (unchanged) |

New files, all under `k8s/production/`:

- `yantra4d-render-worker-deployment.yaml`
- `yantra4d-render-worker-hpa.yaml`
- `yantra4d-render-worker-pdb.yaml`
- `yantra4d-backend-pdb.yaml`
- `yantra4d-render-output-pvc.yaml`

---

## Prerequisite that gates the whole rollout: ReadWriteMany storage

**This is the one thing that can make the change unsafe, and it must be settled
before anything is synced.**

The worker writes finished STL/GLB/3MF artifacts into `/app/backend/static`, and
the API serves them from that same path (`@app.route('/static/<path:filename>')`
→ `send_from_directory(Config.STATIC_DIR)`). There is no object storage in this
platform; the artifact is a file on a disk that both processes can see. While
the worker was a sidecar, "both processes" meant one pod and one `emptyDir`, and
the sharing was implicit.

Splitting the worker into its own pod splits that filesystem. Without a volume
both pods can mount, **every render would succeed and then 404 on download** —
the worker publishes `/static/<file>`, and the API, on a different filesystem,
has never heard of it. The failure is quiet: renders report success, the cache
records a path, and the user gets a broken link.

Hence `yantra4d-render-output`, a **ReadWriteMany** claim mounted by the API and
by every worker replica at `/app/backend/static`.

**Before syncing:**

1. Confirm the cluster has a StorageClass that can provision `ReadWriteMany`
   (NFS, CephFS, Longhorn RWX, EFS, …).
2. Set `storageClassName` in `k8s/production/yantra4d-render-output-pvc.yaml`
   to that class.

If no such class exists, **do not roll this out** — leave the sidecar in place
and record the gap. Do not "fix" a Pending claim by switching it to
`ReadWriteOnce`: the API and the worker will land on different nodes and the
second pod will hang on multi-attach.

The failure mode if the claim never binds is deliberately harmless. The claim is
sync-wave 0; a Pending PVC never reports healthy, so waves 1 and 2 never apply
and the running API keeps its sidecar. Nothing changes until storage is real.

Two other prerequisites, neither of which can take the API down:

- **metrics-server** must be serving `metrics.k8s.io`, or the HPA sits at
  `<unknown>/70%` and never scales. The Deployment still runs at 1 replica.
- The image must be **rebuilt from this commit**, because the worker's
  per-pod heartbeat lives in `apps/worker/render_worker.py`, which ships
  inside the backend image. `deploy.yml` did not treat `apps/worker/**` as a
  backend path — a worker-only change never rebuilt the image — and that is
  fixed in this commit.

---

## Rollout order

Encoded as ArgoCD sync waves, so the order holds even though it is all one
commit. If applying by hand, follow the same three steps.

**Wave 0 — storage and policy.** `yantra4d-render-output` PVC, both PDBs.
Nothing mounts the claim yet. Wait for it to reach `Bound`.

**Wave 1 — the worker.** `yantra4d-render-worker` Deployment, its HPA, its PDB.
The old sidecar is still running at this point, so there are briefly two
consumers of the same Redis queue. That is safe and is the reason for this
order: `BLPOP` hands each job to exactly one consumer, so the two simply share
the queue, and render capacity never drops to zero.

Confirm before continuing:

- worker pods are `Running` and `Ready`;
- `/api/health` reports `workers` ≥ 1 (see below);
- one real render completes and the artifact downloads.

**Wave 2 — the API without the sidecar.** The `yantra4d-backend` Deployment
drops the `render-worker` container and mounts the shared claim instead of the
`emptyDir`. Because the API is `Recreate`, it goes down for the length of a pod
restart — expected, and the reason this is last.

Reversing the order would take the sidecar away before a replacement existed:
with `RENDER_WORKER_REQUIRED=true` the API's readiness probe would 503 on a
missing heartbeat and the kubelet would restart the pod it just started.

### One detail worth not tripping over

The API's render-output volume is **renamed** `render-output` →
`render-output-pvc`. This is not cosmetic. Argo applies with ServerSideApply and
volumes merge on `name`, so turning the existing `emptyDir` into a
`persistentVolumeClaim` under the same name yields one volume carrying two
types — `may not specify more than 1 volume type` — and the Deployment then
fails to apply at all, silently blocking every other change in the file. This
repository has already been bitten by exactly that (see the `analytics-data` →
`analytics-pvc` note in `yantra4d-backend-deployment.yaml`); the rename follows
that precedent.

---

## The heartbeat, and why it had to change

The worker publishes a heartbeat to Redis; the API reads it to decide whether
renders may be accepted, and refuses them when it is stale.

That heartbeat was a **single fleet-wide key**, `yantra_render_worker_heartbeat`,
written by every worker. With one worker that is adequate. With N it breaks in
two ways:

- **The count is unknowable.** The key answers "is something alive", never "how
  many". Behind an HPA that is the only question worth asking, and the old
  readout could not tell one worker from four.
- **A wedged worker hides.** Each worker's readiness probe read the *shared*
  key, so a hung pod kept passing as long as any sibling refreshed it. The probe
  could not fail while any worker lived.

Now each pod writes `render_worker:heartbeat:<pod-name>` (the pod name, wired in
as `RENDER_WORKER_ID` from the downward API), carrying a small JSON payload with
its timestamp and whether it is `idle` or `busy`. The API discovers them with
`SCAN` — never `KEYS`, which blocks the whole Redis server and this runs on the
readiness path — and counts the ones inside the freshness window. Redis TTL
expiry retires dead workers, so there is nothing to reap. Each pod's probes read
only its **own** key, so a wedged pod now fails, restarts, and is replaced.

Two deliberate compatibility choices:

- Workers **also** keep writing the old global key as a bare timestamp. That is
  what makes rollback safe: an API running pre-split code reads only that key,
  and would otherwise see an empty fleet while renders were in fact being
  served. Removing this dual-write is a follow-up, once every reader is on the
  new keys.
- The API **also** reads the old key, counting it as one worker named `legacy`
  when no per-pod keys are present. That covers the wave-1 window, when the
  only worker beating is still the sidecar.

### A latent bug this also fixes

The heartbeat used to be published at the top of the `BLPOP` loop — so it
stopped for the duration of a render. A render legitimately runs up to
`RENDER_TIMEOUT_S` (300s), against a 60s TTL and a `TTL * 2` staleness window in
the API. A long render therefore looked exactly like a dead worker: the API
would start refusing new renders, and with `RENDER_WORKER_REQUIRED=true`
`/api/health/ready` would return 503 and the kubelet would **restart the API pod
mid-render**. That is a real fault in today's single-worker deployment, not only
a scaled one.

The heartbeat now beats from a daemon thread every `TTL/3` (20s), independent of
what the job loop is doing. That is also what makes adding a *liveness* probe on
this key safe — the previous design would have had the probe kill workers for
doing their job.

---

## Scale-down and in-flight renders

The HPA deletes pods directly to scale down and **does not consult the
PodDisruptionBudget** — a PDB bounds voluntary evictions (drains, the eviction
API), not autoscaling. Every scale-down is therefore a chance to interrupt a
render, and a job already popped off the Redis list exists nowhere else: killing
the process loses it outright, with no retry.

Three things bound that:

- the worker traps `SIGTERM` and **drains** — finishes the job in hand, takes no
  new one, then exits. It keeps publishing its heartbeat throughout, reporting
  `busy` or `draining`: a draining worker is still alive and still writing a
  render, and if it went silent while it were the last worker, the API would
  see zero workers, fail readiness and restart itself mid-render;
- `terminationGracePeriodSeconds: 360` gives it room to (300s render ceiling
  plus slack);
- the HPA's `scaleDown` holds for 600s and gives back one pod at a time, so it
  does not thrash.

This does **not** make the queue reliable in general — a `SIGKILL`, an OOM, or a
node failure still drops the job in hand. That is pre-existing (any worker
restart could always do it) and is listed as a follow-up below.

---

## What `/api/health` reports

`/api/health` and `/api/health/ready` are the same handler. The `render_worker`
check now **leads with the fleet size**, because "heartbeat age 3s" reads
identically whether one worker is up or four:

```
"render_worker": {
  "ok": true,
  "detail": "workers 3; busy 1; heartbeat age 4s; queue depth 2; active jobs 1"
}
```

- `workers N` — pods with a heartbeat inside the window. **Always present, even
  at zero**, so "I read nothing" and "I read everything and all is well" cannot
  produce the same line.
- `busy N` — how many of those are mid-render. `workers 4; busy 4` with a
  climbing `queue depth` is the signal that `maxReplicas: 4` is the ceiling.
- `heartbeat age Ns` — age of the freshest heartbeat in the fleet.
- `queue depth N` — `LLEN yantra_render_queue`, the true backlog.
- `active jobs N` — jobs currently being processed fleet-wide.

`ok` is still "at least one live worker", and `RENDER_WORKER_REQUIRED=true`
still turns a false `ok` into `status: unhealthy` and HTTP 503. During wave 1
expect `workers 1` with the worker named `legacy` — that is the sidecar, and it
is correct.

Full detail, including per-worker ids, is on
`render_orchestrator.get_render_worker_status()`.

---

## Rollback

**After wave 1, before wave 2** — nothing has been taken away yet. Scale the
worker Deployment to 0 or delete it; the sidecar is still serving renders. No
API impact.

**After wave 2** — revert the commit and re-sync. The API regains its sidecar
and its `emptyDir`; the worker Deployment, HPA and PDBs are pruned. Two things
make this safe:

- the new workers dual-write the legacy heartbeat key, so a reverted API still
  sees a live worker while the standalone workers drain;
- the volume rename means the revert re-adds `render-output` as a *new* list
  entry rather than trying to change an existing volume's type.

In-flight renders at the moment of revert are lost, and artifacts on the shared
claim become unreachable once the API returns to its `emptyDir`. Renders are
reproducible from their parameters, so this costs time, not data.

Leave the `yantra4d-render-output` claim in place on rollback — deleting it
destroys the artifacts, and an unused Bound claim costs only storage.

---

## Follow-ups (not in this change)

- **Queue-depth autoscaling.** CPU is a lagging proxy: it only rises once work
  is already being done, so the HPA always reacts a step late. The metric this
  workload wants is `LLEN yantra_render_queue` — the actual backlog, which
  rises the instant a user waits. Serving it to an HPA needs a custom-metrics
  adapter that does not exist in this cluster (Prometheus Adapter over a
  Redis exporter, or KEDA's Redis list scaler, which fits this shape more
  directly). Nothing here approximates it, and the CPU target of 70% is a
  starting point to revisit against a week of real load.
- **At-least-once job delivery.** `BLPOP` removes the job from Redis before it
  is done, so any hard stop loses it. `BLMOVE` into a per-worker processing
  list, with a reaper for lists whose worker's heartbeat has expired, would make
  the queue recoverable. The per-pod heartbeat keys this change introduces are
  what such a reaper needs to identify a dead worker.
- **Drop the legacy heartbeat dual-write**, once no pre-split reader remains.
- **Object storage for render artifacts.** Would remove the RWX requirement
  entirely, and with it the shared-filesystem coupling between API and worker.
  The larger correct answer to what the PVC works around.
- **API to 2+ replicas.** Blocked on the ReadWriteOnce analytics PVC and the
  `Recreate` strategy. When that is resolved, flip `yantra4d-backend-pdb.yaml`
  to `minAvailable: 1`, which only then begins to protect anything.
