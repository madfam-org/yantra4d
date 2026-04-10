# AI Features — Configurator, Code Editor & Synthesizer

Yantra4D includes three AI-powered features that use LLMs to assist with parametric design.

## Overview

| Feature | Description | Tier Required |
|---------|-------------|---------------|
| **AI Configurator** | Chat-based parameter adjustment — describe what you want and the AI adjusts params | essentials+ |
| **AI Code Editor** | Natural language SCAD editing — describe changes and the AI generates search/replace edits | pro+ |
| **AI Synthesizer** | Generate an entire Yantra4D project (manifest + SCAD files) from a natural language prompt | pro+ |

All features use streaming SSE responses for real-time feedback.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `anthropic` | LLM provider: `anthropic` or `openai` |
| `AI_API_KEY` | — | **Required**. API key for the selected provider |
| `AI_MODEL` | Provider default | Override model name (optional) |
| `AI_MAX_TOKENS` | `2048` | Max response tokens per request |

### Default Models

| Provider | Default Model |
|----------|---------------|
| Anthropic | `claude-sonnet-4-20250514` |
| OpenAI | `gpt-4o` |

If `AI_API_KEY` is not set, AI endpoints return `503 AI features are not configured`.

## AI Configurator

The configurator lives in `AiChatPanel.jsx` (mode: `configurator`) and talks to the backend via `ai_configurator.py`.

### How It Works

1. User types a request like "make it wider and shorter"
2. Backend builds a system prompt with all parameter names, ranges, current values
3. LLM responds with explanation + JSON parameter changes
4. Backend validates changes against manifest constraints (min/max/step)
5. Validated changes stream back as SSE events
6. Frontend applies the changes to the parameter state

### Parameter Validation

The backend clamps all AI-suggested values:

- Numeric values clamped to `[min, max]`
- Values rounded to nearest `step` (if step > 0)
- Unknown parameter IDs silently dropped
- Boolean parameters explicitly converted

## AI Code Editor

The code editor lives in `ScadEditor.jsx` (AI toggle button) and talks to `ai_code_editor.py`.

### How It Works

1. User opens SCAD files in the Monaco editor
2. User toggles AI panel and describes desired changes
3. Backend receives all open file contents + the user's request
4. LLM responds with explanation + search/replace edits
5. Backend validates each edit (file exists, search string found)
6. Validated edits stream back and are applied client-side

### Edit Format

Edits use exact string matching (not line numbers) for robustness:

```json
{
  "edits": [
    {
      "file": "main.scad",
      "search": "cube([10, 10, 10])",
      "replace": "cube([20, 10, 15])"
    }
  ]
}
```

## AI Synthesizer

The synthesizer generates an entire Yantra4D "Cartridge" (manifest + SCAD files) from a natural language description. It lives in `SynthesisModal.jsx` (frontend) and `ai_synthesizer.py` (backend).

### How It Works

1. User opens the Synthesis modal and describes a project (e.g., "a parametric phone stand with adjustable angle")
2. Backend creates a temporary session in `synthesizer` mode
3. LLM receives a zero-shot prompt that defines the Yantra4D Cartridge schema
4. LLM streams a response containing explanation text + a JSON code block with the cartridge
5. Backend parses the JSON (`parse_synthesis()`) extracting `slug`, `manifest`, and `files`
6. On success, writes the project to disk (`PROJECTS_DIR/{slug}/project.json` + SCAD files)
7. Frontend receives the `cartridge` SSE event and redirects to the new project

### Cartridge Structure

The LLM generates a JSON block containing:

```json
{
  "slug": "phone-stand",
  "manifest": {
    "project": { "name": "Phone Stand", "slug": "phone-stand", "version": "1.0.0" },
    "modes": [{ "id": "main", "scad_file": "main.scad", "parts": ["part1"] }],
    "parts": [{ "id": "part1", "render_mode": 0, "default_color": "#e5e7eb" }],
    "parameters": [{ "id": "angle", "type": "slider", "min": 15, "max": 75, "default": 45 }]
  },
  "files": {
    "main.scad": "angle = 45;\n// OpenSCAD geometry..."
  }
}
```

### Collision Handling

If a project with the generated slug already exists, a 4-character UUID suffix is appended (e.g., `phone-stand-a3f2`) to avoid overwriting.

## API Reference

### Create Session

```
POST /api/ai/session
Content-Type: application/json

{
  "project": "gridfinity",
  "mode": "configurator"
}
```

Modes: `configurator`, `code-editor`, `synthesizer`

Response: `{ "session_id": "uuid" }` or `429` if per-user session limit (5) reached.

### Stream Chat

```
POST /api/ai/chat-stream
Content-Type: application/json

{
  "session_id": "uuid",
  "message": "make it taller",
  "current_params": { "height": 50 }
}
```

Response: SSE stream with events:

| Event | Payload | Description |
|-------|---------|-------------|
| `chunk` | `{ "text": "I'll..." }` | Incremental LLM text |
| `params` | `{ "changes": { "height": 80 } }` | Validated parameter changes (configurator) |
| `edits` | `{ "edits": [...] }` | Validated code edits (code editor) |
| `done` | `{}` | Stream complete |
| `error` | `{ "error": "msg" }` | Error occurred |

### Synthesize Project

```
POST /api/ai/synthesize
Content-Type: application/json

{
  "prompt": "a parametric phone stand with adjustable angle and width"
}
```

Response: SSE stream with events:

| Event | Payload | Description |
|-------|---------|-------------|
| `chunk` | `{ "text": "..." }` | Incremental LLM text |
| `cartridge` | `{ "cartridge": {...}, "slug": "phone-stand" }` | Generated project (written to disk) |
| `done` | `{}` | Stream complete |
| `error` | `{ "error": "msg" }` | Error occurred |

## Tier Access

| Tier | Configurator | Code Editor | Synthesizer | Requests/Hour |
|------|:---:|:---:|:---:|:---:|
| guest | — | — | — | 0 |
| essentials | Yes | — | — | 20 |
| pro | Yes | Yes | Yes | 100 |
| madfam | Yes | Yes | Yes | 300 |

## Session Management

### Basic Behavior

- Sessions expire after **1 hour** (`MAX_AGE = 3600`)
- Conversation history is maintained within a session for multi-turn refinement
- Expired sessions return `404 Session not found or expired`
- Per-user limit: **5 concurrent sessions** (`MAX_SESSIONS_PER_USER = 5`). Exceeding returns `429`.

### Storage Backends

| Backend | When Active | Behavior |
|---------|-------------|----------|
| **In-memory** | `REDIS_URL` not set or Redis unreachable | Sessions lost on pod restart. Cleanup on each `create_session()` call |
| **Redis** | `REDIS_URL` set and connection healthy | Sessions persist across restarts. TTL-based expiry (`SETEX` with `MAX_AGE`) |

### Circuit Breaker (Redis resilience)

The session store uses a circuit breaker pattern to handle Redis failures gracefully:

1. **Closed** (normal): All operations go to Redis. Each success resets the failure counter.
2. **Counting failures**: On Redis error, failure count increments. A warning is logged per failure.
3. **Open** (fallback): After **3 consecutive failures** (`_REDIS_CIRCUIT_THRESHOLD`), the circuit opens for **60 seconds** (`_REDIS_CIRCUIT_COOLDOWN`). All operations fall back to in-memory during this window.
4. **Half-open**: After the cooldown, the next operation attempts Redis again. Success resets the circuit; failure re-opens it.

Key functions in `ai_session.py`: `_redis_available()`, `_redis_success()`, `_redis_failure()`.

### Distributed Locking

Session updates use Redis-based distributed locks to prevent race conditions in multi-worker deployments:

- Lock key: `ai_session_lock:{session_id}`
- TTL: **5 seconds** (`LOCK_TTL_SECONDS`) — auto-releases if worker crashes
- Non-blocking: if lock acquisition fails, the update proceeds without the lock (logged as warning)
- In-memory mode: locking is skipped (single-process, no contention)

Key functions: `_acquire_lock()`, `_release_lock()`.

### Schema Validation

Session data is validated via the `SessionData` dataclass on every read:

```python
@dataclass
class SessionData:
    project_slug: str           # Required, non-empty string
    mode: str                   # Must be: configurator | code-editor | synthesizer
    messages: list[dict]        # Conversation history
    created_at: float           # Unix timestamp
    user_id: str | None         # For per-user session limits
```

Invalid sessions (corrupted data, wrong types) are treated as expired and silently removed.

**Production note**: When `REDIS_URL` is not set and `FLASK_DEBUG` is not `true`, the backend logs a warning: *"REDIS_URL not set: AI sessions will be lost on pod restart."* For multi-worker or auto-scaling deployments, configure Redis to persist sessions across restarts.

## Frontend Components

| Component | File | Purpose |
|-----------|------|---------|
| `AiChatPanel` | `components/ai/AiChatPanel.jsx` | Chat UI (configurator + code editor modes) |
| `SynthesisModal` | `components/studio/SynthesisModal.jsx` | Project synthesis modal |
| `useAiChat` | `hooks/ai/useAiChat.ts` | SSE streaming hook |
| `ScadEditor` | `components/editor/ScadEditor.jsx` | Monaco editor + AI toggle |
| `aiService` | `services/domain/aiService.ts` | API client for AI endpoints |
