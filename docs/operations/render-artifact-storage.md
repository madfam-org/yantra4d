# Render artifact storage

**Status:** shipped, **off by default**. `RENDER_ARTIFACT_STORE` defaults to
`fs`, which is the behaviour this platform has always had. Nothing about
production changes until an operator sets it to `s3`, and the bucket is
provisioned through Enclii — this repository contains no MinIO Deployment.

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

## Migration

There is no artifact backfill and none is wanted. Render artifacts are
regenerable by definition — that is what the render cache is for.

1. **Provision the bucket** through Enclii (this repo has no MinIO manifest, by
   design; the operator owns that). Create the credentials as
   `RENDER_ARTIFACT_S3_ACCESS_KEY_ID` / `RENDER_ARTIFACT_S3_SECRET_ACCESS_KEY`
   in the `yantra4d-secrets` Secret — the Deployment maps them onto the
   `AWS_*` names both containers read.
2. **Flip the flag** on both containers of `yantra4d-backend` at once. They must
   agree: an API on `fs` and a worker on `s3` is precisely the split-brain this
   change removes.
3. **New renders go to the selected store.** Nothing migrates old ones.
4. **Cache entries whose key is missing in the store are treated as cache
   misses.** `RenderCache` validates an entry with `ArtifactStore.exists`, not
   `os.path.isfile`, so entries pointing at artifacts on the old backend simply
   do not resolve and the part is rendered again. That is what makes the flip
   safe in *both* directions.
5. **Rollback is flipping the flag back.** Same rule in reverse: entries written
   against the bucket stop resolving, and renders repopulate the local
   directory. No data has to be moved and nothing has to be cleaned up first.

Redis L2 cache entries written before this change carry an absolute `path`
rather than a `key`. Their basename *is* the key the flat static directory
used, so they keep hitting rather than turning the rollout into a cold cache.
That fallback can be deleted once `RENDER_CACHE_REDIS_TTL` (24h) has elapsed
past the rollout.

---

## Differences to know about before flipping to `s3`

**Cache-Control on `/static` changes from `no-cache` to `public, max-age=3600`.**
This is a consequence of a pre-existing quirk, not of object storage.
`Flask(__name__)` registers a built-in `static` endpoint for `/static/<path>`,
and `app.py` registers its own `serve_static` view for the same URL; Werkzeug
resolves the tie in registration order, so **the built-in rule wins and
`serve_static` has never run in production** — its `public, max-age=3600` line
has never applied, and artifacts go out `no-cache`. (`app.py` already knew the
two rules were ambiguous: that is why #78's private-artifact gate is a
`before_request` hook rather than a check inside the view.) With a
non-filesystem store there is no local directory to serve from, the built-in
rule is not registered, and the app's own view finally runs.

The result is safe — artifact names carry the parameter hash, so a cached
response can never be a stale render, and a private project's artifact is still
stamped `private, no-store` by the gate, which runs after the view — but it is
a real change in what browsers and any CDN will do, and it should not be
discovered in production.

**No `Range` and no conditional revalidation on the streaming path.** The
object store is not asked for either. The viewer and download clients fetch
meshes whole, so this costs nothing today; a partial-content client would get a
full body.

**The render GC and the read-side scanners are filesystem-only.** These are
recorded gaps, not silent ones:

- `services/engine/render_gc.py` sweeps the local directory. Under `s3` it
  collects the worker's scratch files (which the worker also removes itself
  after a successful publish) but not bucket objects. Object lifetime under
  `s3` belongs to a **bucket lifecycle rule** — set one, matching
  `RENDER_GC_TTL` (24h), when provisioning the bucket.
- `routes/engine/verify.py`, `routes/engine/analysis.py` and
  `routes/engine/simulate.py` find "the latest render" by globbing the static
  directory. Under `s3` they find nothing and report no render available. They
  are unchanged here; moving them onto the store is follow-up work.

---

## What each component does now

| Component | Behaviour |
|---|---|
| `apps/api/services/storage/` | `ArtifactStore` (put from path/bytes, open, exists, size, delete) + `fs` and `s3` backends + the factory. |
| `apps/worker/render_worker.py` | Engines still render to a real local path — they are subprocesses. The finished artifact and its GLB companion are then published through the store; under `s3` the scratch copies are removed. A failed publish **fails the render** rather than reporting a URL that does not resolve. |
| `services/engine/render_cache.py` | Records the artifact's **store key**, not an absolute path, and validates entries with `ArtifactStore.exists`. |
| `app.py` → `/static/<path>` | Reads through the store. Filesystem: unchanged `send_from_directory`. Object store: streamed, and Flask's built-in static rule is not registered so a stray local file cannot shadow the bucket. |
| `routes/engine/download.py` | Render artifacts come from the store (streamed, never redirected); a project's checked-in `exports/` files still come from the project directory. |
| `routes/core/health.py` | Reports the store kind and whether it answers. |
| `routes/editor/git_ops.py`, `routes/projects/animations.py`, `_render_static_part` | Also publish through the store — they render in the API process but serve from `/static`, so they would otherwise 404 under `s3`. |

## Relationship to the dedicated render worker (#88)

`docs/operations/render-worker-capacity.md` splits the worker into its own
Deployment and shares artifacts with a **ReadWriteMany PVC**. This change is the
alternative to that PVC: with `RENDER_ARTIFACT_STORE=s3` the two pods need no
shared filesystem at all, and the RWX StorageClass prerequisite — the one thing
that can block that rollout — disappears. The two are compatible; only the
sharing mechanism differs. Neither is enabled here.
