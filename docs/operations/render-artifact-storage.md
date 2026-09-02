# Render artifact storage

**Status:** shipped, **off by default**. `RENDER_ARTIFACT_STORE` defaults to
`fs`, which is the behaviour this platform has always had. Nothing about
production changes until an operator sets it to `s3`, and the bucket is
provisioned through Enclii — this repository contains no MinIO Deployment.

Both directions go through the store: renders are written through it, and
every read that used to walk the static directory — serving `/static`, the
download route, the artifact GC, "the latest render" lookups, the verifier —
asks it instead. See [Operator flip runbook](#operator-flip-runbook).

---

## Why

A finished render is an STL/GLB/3MF file. The **render worker** writes it into
`/app/backend/static`; the **API** serves it back from that same path
(`/static/<name>`, and the project download endpoints). Today those are two
containers in one pod sharing a `render-output` `emptyDir`, so "both processes"
means one filesystem and the sharing is implicit.

That implicit sharing is the thing standing between this platform and a render
worker that can scale. Splitting the worker into its own Deployment splits the
filesystem, and then **every render succeeds and then 404s on download** — the
worker publishes `/static/<name>`, the API has never heard of that file, the
render cache records it as present, and the user gets a broken link. The
failure is quiet, which is the worst property it could have. The dedicated
worker Deployment (#88) works around it with a ReadWriteMany PVC, which is
correct but requires an RWX StorageClass the cluster may not have.

This change puts a seam where the filesystem was: an **artifact store** with a
key-addressed interface and two backends. Producers `put` an artifact under a
key; readers `open` it by that key; where the bytes live is configuration.

```
                    ┌──────────── RENDER_ARTIFACT_STORE ────────────┐
                    │                                               │
  render worker ────┤  fs   → /app/backend/static (today, default)  ├──── API
  (put_file)        │  s3   → bucket/prefix/<key> (MinIO, opt-in)   │     (open/stream)
                    └───────────────────────────────────────────────┘
```

### What did *not* change, deliberately

**URLs.** An artifact is still `/static/<slug>_preview_<paramhash>_<part>.<fmt>`
on both backends. That is not cosmetic: the private-project gate added in #78
(`services/core/project_access.py`) and the download route's access checks both
work by parsing the **name**. Move the bytes, keep the name, and both keep
applying with no change at all.

**Nothing is ever redirected to a bucket.** There is no presigned-URL or
public-bucket path in `S3ArtifactStore`, on purpose. Object-storage artifacts
are *streamed through the API*, so every request still passes the privacy gate
and the tier gate. A bucket URL handed to a browser would route around both,
and a private cartridge's geometry would be one guessable object name away from
anyone.

**The filesystem backend is a no-op.** A render already writes into the static
directory, so publishing such a file must not copy it: copying would double the
bytes on a volume with a hard `sizeLimit`, reset the mtime the GC sorts on, and
swap the inode under an in-flight download. `FilesystemArtifactStore.put_file`
detects sameness with `os.path.samefile` and returns. The read path likewise
stays on Flask's `send_from_directory`/`send_file`, so `ETag`, `Last-Modified`,
`Content-Length`, conditional 304s, range requests and the zero-copy send are
all exactly what they were. `tests/e2e/test_artifact_store_serving.py` compares
the real responses against the pre-change Flask calls, header for header.

**The two backends answer identically.** Not "similarly": the same app is
driven with each store installed in turn and the responses are diffed header
for header — status, `Content-Type`, `Content-Length`, `Content-Range`,
`Cache-Control`, `Accept-Ranges`, `Content-Disposition`, and the presence of
`ETag` and `Last-Modified` (their *values* differ by construction — S3 hands
back the object's MD5, a file's is derived from mtime and size). Ranges,
conditional revalidation, the JSON 404 and the private-project 403 all match.
That comparison is the contract the flag is safe to flip against, and it is
what caught the two divergences an earlier cut of this branch had.

---

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `RENDER_ARTIFACT_STORE` | `fs` | `fs` — today's directory (`Config.STATIC_DIR`). `s3` — an S3-compatible bucket. Any other value **refuses to start**. |
| `RENDER_ARTIFACT_S3_ENDPOINT` | *(unset)* | Base URL of the S3-compatible endpoint. Leave unset for real AWS S3. |
| `RENDER_ARTIFACT_S3_BUCKET` | *(unset)* | Bucket name. Required when the store is `s3`. |
| `RENDER_ARTIFACT_S3_REGION` | `us-east-1` | Region. MinIO ignores it but botocore requires one. |
| `RENDER_ARTIFACT_S3_PREFIX` | *(unset)* | Key namespace inside the bucket, e.g. `renders/v1`. Lets one bucket hold more than one environment. |
| `AWS_ACCESS_KEY_ID` | *(unset)* | Read by botocore from the environment. **Never** a config field — see below. |
| `AWS_SECRET_ACCESS_KEY` | *(unset)* | As above. |
| `AWS_SESSION_TOKEN` | *(unset)* | As above, for temporary credentials. |

Credentials are deliberately absent from `apps/api/config.py`. botocore reads
the standard `AWS_*` variables itself, so no secret is ever held on a config
object that gets logged at startup, and `describe()` — which feeds the startup
log — has nothing to leak. In Kubernetes they come from the `yantra4d-secrets`
Secret with `optional: true`, so **the pod starts without them** and falls back
to the `fs` default.

Addressing is **path-style** (`endpoint/bucket/key`). Virtual-host addressing
needs wildcard DNS and a wildcard certificate, which no in-cluster MinIO has.

### Fail closed at startup

With `RENDER_ARTIFACT_STORE=s3`, both the API app factory and the render
worker's entry point call `check_artifact_store_ready()` before serving or
consuming anything. It issues a `HeadBucket`; an unreachable or non-existent
bucket, or rejected credentials, **raises and the process dies**, with a message
naming the likely cause. Starting anyway would accept renders, publish them
nowhere, and hand back URLs that 404 — the exact quiet failure this whole change
exists to prevent.

`/api/health` reports which backend took effect, as
`artifact_store: "fs" | "s3"` and `checks.artifact_store`. It reports the
**kind only** — never the endpoint, bucket or prefix. That endpoint is
unauthenticated and rate-limit exempt, so it is not a place to name
cluster-internal addresses; an operator reads those from the startup log.

---

## Operator flip runbook

**Prerequisite — provision, outside this repo.** The bucket and its credentials
are created through Enclii; this repository contains no MinIO or bucket
manifest, by design. Give the bucket a lifecycle rule expiring objects at
24 hours, matching `RENDER_GC_TTL`.

**Step 1 — put the credentials in the Secret.** The `yantra4d-secrets` Secret
takes two keys, referenced by name only; their values live in Enclii and are
never written here or in any manifest:

| Secret key | Mapped to the container env var |
|---|---|
| `RENDER_ARTIFACT_S3_ACCESS_KEY_ID` | `AWS_ACCESS_KEY_ID` |
| `RENDER_ARTIFACT_S3_SECRET_ACCESS_KEY` | `AWS_SECRET_ACCESS_KEY` |
| `RENDER_ARTIFACT_S3_ENDPOINT` | `RENDER_ARTIFACT_S3_ENDPOINT` |

All three are referenced with `optional: true` in
`k8s/production/yantra4d-backend-deployment.yaml`, so the pod starts without
them and stays on the `fs` default. Add them before step 2, not with it.

**Step 2 — set the plain configuration on *both* containers.**
`RENDER_ARTIFACT_S3_BUCKET`, `RENDER_ARTIFACT_S3_REGION` and
`RENDER_ARTIFACT_S3_PREFIX` are not secret and live in the Deployment. The API
and the worker must agree: an API on `fs` and a worker on `s3` is exactly the
split-brain this change removes.

**Step 3 — flip `RENDER_ARTIFACT_STORE` from `fs` to `s3` on both containers,
in one rollout.**

**Step 4 — watch the pod come up, or not.** Both containers issue a
`HeadBucket` before serving or consuming anything; an unreachable bucket or
rejected credentials **kills the process at startup** with a message naming the
likely cause. A pod that is running has a bucket it can reach.

**Step 5 — confirm.** `GET /api/health` reports
`artifact_store: "s3"` and `checks.artifact_store.ok`. It reports the **kind
only** — the endpoint, bucket and prefix stay out of an unauthenticated,
rate-limit-exempt response; read those from the startup log. Then render
something and download it: the URL shape does not change, so a working
`/static/<name>` on a fresh render is the end-to-end proof.

**Rollback — set `RENDER_ARTIFACT_STORE` back to `fs`.** That is the whole
procedure. Nothing has to be migrated, drained or cleaned up first, because:

- artifacts are regenerable by definition — that is what the render cache is
  for, and there is no backfill in either direction;
- a cache entry naming a key the current store does not hold is simply a
  **miss** (`RenderCache` validates with `ArtifactStore.exists`), so entries
  written against the bucket stop resolving and the part is rendered again;
- URLs are identical on both backends, so nothing the studio holds goes stale.

Leaving the credentials in the Secret after a rollback is harmless — nothing
reads them while the store is `fs`.

Redis L2 entries written before this change carry an absolute `path` rather
than a `key`. Their basename *is* the key the flat static directory used, so
they keep hitting rather than turning the rollout into a cold cache. That
fallback can be deleted once `RENDER_CACHE_REDIS_TTL` (24 h) has elapsed past
the rollout.

---

## Differences to know about before flipping to `s3`

Short list, and none of it is a behaviour change in the API's responses.

**Latency, not semantics.** Every artifact read becomes a network round trip to
the bucket instead of a page-cache hit. A `HEAD` per request answers "is it
there, how big, what validator" — which is also what makes a conditional
request cheap, since a 304 costs that `HEAD` and no object body. Ranged reads
are pushed down as `Range` headers, so a partial fetch does not drag a whole
mesh through the API pod.

**The render GC's *size* pass does not run.** Age expiry does, identically:
anything older than `RENDER_GC_TTL` (24 h) is deleted from the bucket. The size
pass exists to keep a specific `emptyDir` under the `sizeLimit` the kubelet
evicts on, and `RENDER_VOLUME_LIMIT_BYTES` (512 MiB) describes *that volume* —
enforcing it as if it were bucket capacity would delete fresh renders on a busy
day. **Set a bucket lifecycle rule matching `RENDER_GC_TTL` when provisioning
the bucket**, as belt and braces behind the sweep.

**Routes that need a real file download one.** The verifier subprocess,
trimesh-based analysis, the FEA overlay, the Cotiza quote and a printer upload
all take a path, not a stream. Under `s3` the artifact is fetched to a
temporary file for the duration of the request and removed afterwards
(`services.storage.local_artifact`). Under `fs` the artifact's own path is
handed over and nothing is copied. Budget disk for one concurrent mesh per
in-flight request of those kinds.

**Nothing else.** In particular: `Cache-Control` is `no-cache` on both backends
(`/static` is served by one store-backed rule now, on both), `Range` and
conditional revalidation work on both, and a private project's artifact is
`private, no-store` with no validator reaching an unentitled caller on both.

---

## What each component does now

| Component | Behaviour |
|---|---|
| `apps/api/services/storage/` | `ArtifactStore` (put from path/bytes, `open` with an optional byte range, `stat`, `list`, `exists`, `size`, `delete`, `local_path`/`fetch_to_path`) + `fs` and `s3` backends + the factory, plus `local_artifact()` for callers that need a real file. |
| `apps/worker/render_worker.py` | Engines still render to a real local path — they are subprocesses. The finished artifact and its GLB companion are then published through the store; under `s3` the scratch copies are removed. A failed publish **fails the render** rather than reporting a URL that does not resolve. |
| `services/engine/render_cache.py` | Records the artifact's **store key**, not an absolute path, and validates entries with `ArtifactStore.exists`. |
| `app.py` → `/static/<path>` | **One** rule, on both backends, reading through the store — Flask's built-in `static` endpoint is no longer registered, so it can neither shadow the app's view nor serve a stray local file in place of a bucket object. Filesystem: unchanged `send_from_directory`. Object store: streamed, with `ETag`, `Last-Modified`, `If-None-Match`/`If-Modified-Since` → 304, `Range` → 206/416 and `If-Range`. |
| `services/engine/render_gc.py` | Lists and deletes through the store, so age expiry works identically on both backends. The size pass stays filesystem-only — see above. |
| `services/engine/render_artifacts.py` | One `find_latest_render_key()` for the three routes that each had their own `glob` over the static directory, plus `discard_render_artifacts()` for superseding a previous render. |
| `routes/engine/verify.py`, `routes/engine/analysis.py`, `routes/engine/simulate.py`, `routes/integrations/cotiza_export.py`, `routes/integrations/printer.py` | Locate the artifact through the store and materialise it with `local_artifact()` — the artifact's own path under `fs`, a temporary download under `s3`. |
| `routes/engine/download.py` | Render artifacts come from the store (streamed, never redirected); a project's checked-in `exports/` files still come from the project directory. |
| `routes/core/health.py` | Reports the store kind and whether it answers. |
| `routes/editor/git_ops.py`, `routes/projects/animations.py`, `_render_static_part` | Also publish through the store — they render in the API process but serve from `/static`, so they would otherwise 404 under `s3`. |

## What this leaves of the worker Deployment split (ADR-014, #88)

`docs/operations/render-worker-capacity.md` splits the render worker into its
own Deployment and shares artifacts with a **ReadWriteMany PVC**. This change
is the alternative to that PVC: with `RENDER_ARTIFACT_STORE=s3` the two pods
need no shared filesystem at all, and the RWX StorageClass prerequisite — the
one thing that can block that rollout — disappears.

ADR-014's premise was that the split had to wait on this, because splitting the
pod first would make every render succeed and then 404 on download, quietly.
With the seam in place and both sides of it — write *and* read — going through
the store, **what is left of the split is small, and none of it is about
artifacts**:

- a second Deployment manifest and its own resource requests and replica count
  (the container image, command and environment are already the ones the
  worker sidecar runs);
- moving the `render-output` `emptyDir` mount to worker-only, and dropping it
  from the API container — under `s3` the API never touches that directory,
  and the worker uses it purely as scratch it deletes after each publish;
- a HorizontalPodAutoscaler on the Redis queue depth, which is the point of
  splitting at all;
- keeping the two in step on `RENDER_ARTIFACT_STORE`. They must agree: an API
  on `fs` and a worker on `s3` is the split-brain this whole change removes.
  Two Deployments make that a configuration invariant rather than a shared
  block of YAML, so it wants a check — the startup log names the backend on
  both, and `/api/health` names the API's.

The ordering is therefore: flip to `s3`, confirm the platform is happy on it,
*then* split. The split no longer carries the artifact problem, and rolling it
back does not require rolling back storage.

Neither is enabled here.
