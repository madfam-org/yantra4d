# Async Render Architecture

Design document for migrating Yantra4D's synchronous render pipeline to an asynchronous task-queue architecture.

## Current Architecture

```
Client → Flask route → subprocess.run(openscad) → response
                       └── blocking, per-request, in-process
```

- Renders are synchronous subprocess calls (`subprocess.run()` / `subprocess.Popen()`)
- `ProcessManager` tracks one active render per process
- Timeout handled via `threading.Timer` (stream) or `subprocess.run(timeout=)` (sync)
- No concurrency control beyond rate limiting
- Each gunicorn worker can run one render at a time

## Problems

1. **Worker starvation**: A long render blocks an entire gunicorn worker
2. **No horizontal scaling**: Render capacity = worker count
3. **No per-user concurrency**: A single user can monopolize all workers
4. **No retry/resume**: If a worker dies mid-render, the work is lost
5. **Memory pressure**: OpenSCAD can use >1GB RAM; 4 concurrent renders = 4GB

## Proposed Architecture

```
Client → Flask route → Task Queue (Redis) → Worker Pool → Result Store
              │              │                    │              │
              │         Redis Broker          K8s Pods      Redis + Disk
              │              │                    │              │
              └──── Poll/SSE ┘                    └── Callback ──┘
```

### Components

#### Task Queue (Celery or RQ)
- **Broker**: Redis (already deployed, DB 0)
- **Result backend**: Redis (DB 3) with TTL
- **Serializer**: JSON (render params are JSON-safe)

#### Worker Deployment
- Separate K8s Deployment: `yantra4d-worker`
- Same Docker image as backend (shares OpenSCAD binary)
- `CELERY_WORKER=true` env flag selects worker entrypoint
- HPA: scale 2-10 based on queue depth metric

#### Render Task
```python
@celery.task(bind=True, max_retries=1, soft_time_limit=240, time_limit=300)
def render_part(self, project_slug, scad_path, params, part, render_mode, export_format):
    """Execute a single part render as a Celery task."""
    output_path = _make_output_path(project_slug, params, part, export_format)
    cmd = build_openscad_command(output_path, scad_path, params, render_mode)
    success, stderr = run_render(cmd, scad_path=scad_path)
    if not success:
        raise RenderError(stderr)
    return RenderResult(
        success=True,
        output_path=output_path,
        stderr=stderr,
        duration_ms=...,
    )
```

#### Concurrency Limits
- Per-user: max 2 concurrent renders (enforced via Redis semaphore)
- Global: max `RENDER_CONCURRENCY` (default: 8, configurable per tier)
- Queue priority: madfam > pro > basic > guest

#### Sync Facade (Backward Compatibility)
```python
def render_sync(project_slug, scad_path, params, parts, ...):
    """Blocking wrapper — dispatches to queue, polls until complete."""
    tasks = [render_part.delay(...) for part in parts]
    results = [t.get(timeout=RENDER_TIMEOUT_S) for t in tasks]
    return results
```

The existing `/api/render` endpoint uses `render_sync()` internally — no API change.

#### SSE Streaming
```python
def render_stream(project_slug, ...):
    """SSE generator — dispatches to queue, yields progress events."""
    tasks = [render_part.delay(...) for part in parts]
    for task in tasks:
        while not task.ready():
            # Poll task state, yield progress events
            yield sse_event(...)
            time.sleep(0.5)
        yield sse_event('part_done', task.result)
    yield sse_event('complete', ...)
```

### Migration Path

#### Phase 1: Refactor `run_render()` return type
- Return `RenderResult` dataclass instead of `tuple[bool, str]`
- Non-breaking internal change
- **Status: Included in this plan (Phase 8)**

#### Phase 2: Add Celery infrastructure
- Add `celery` to requirements.txt
- Create `apps/api/tasks/render.py` with `render_part` task
- Create `apps/api/celery_app.py` for Celery configuration
- Add `yantra4d-worker` to docker-compose.yml
- Feature-flagged: `ASYNC_RENDER=true` enables queue, `false` uses direct subprocess

#### Phase 3: Wire routes to task queue
- `/api/render` → `render_sync()` (blocking wrapper)
- `/api/render-stream` → SSE polling of task state
- `/api/render-cancel` → `task.revoke(terminate=True)`

#### Phase 4: K8s deployment
- Add worker Deployment manifest
- HPA based on Celery queue length (via prometheus-celery-exporter)
- Resource limits: 2 CPU, 2Gi memory per worker pod

### Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `ASYNC_RENDER` | `false` | Enable task queue rendering |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/3` | Result store |
| `RENDER_CONCURRENCY` | `8` | Max global concurrent renders |
| `RENDER_USER_CONCURRENCY` | `2` | Max per-user concurrent renders |
| `CELERY_WORKER` | `false` | Run as worker (not web server) |

### Monitoring

- Celery Flower dashboard (optional, dev only)
- Prometheus metrics via `celery-exporter`
- Queue depth → HPA scaling trigger
- Task duration histograms → render performance tracking

### Risks

1. **Complexity**: Celery adds operational overhead (broker, workers, monitoring)
2. **Latency**: Queue dispatch adds ~50-100ms per render
3. **File access**: Workers need shared filesystem (or S3) for render outputs
4. **State management**: SSE streaming requires polling instead of direct pipe

### Decision

This is a **future implementation**. The current synchronous architecture handles the current load. Implement when:
- Worker starvation becomes a measurable problem
- User concurrency exceeds 4 workers regularly
- Horizontal scaling is needed beyond single-node deployment
