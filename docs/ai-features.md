# AI Features — Configurator & Code Editor

Qubic includes two AI-powered features that use LLMs to assist with parametric design.

## Overview

| Feature | Description | Tier Required |
|---------|-------------|---------------|
| **AI Configurator** | Chat-based parameter adjustment — describe what you want and the AI adjusts params | basic+ |
| **AI Code Editor** | Natural language SCAD editing — describe changes and the AI generates search/replace edits | pro+ |

Both features use streaming SSE responses for real-time feedback.

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

Response: `{ "session_id": "uuid" }`

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

## Tier Access

| Tier | Configurator | Code Editor | Requests/Hour |
|------|:---:|:---:|:---:|
| guest | — | — | 0 |
| basic | Yes | — | 30 |
| pro | Yes | Yes | 100 |
| madfam | Yes | Yes | 300 |

## Sessions

- Sessions are stored **in-memory** (not persisted across server restarts)
- Sessions expire after **1 hour**
- Conversation history is maintained within a session for multi-turn refinement
- Expired sessions return `404 Session not found or expired`

## Frontend Components

| Component | File | Purpose |
|-----------|------|---------|
| `AiChatPanel` | `components/AiChatPanel.jsx` | Chat UI (both modes) |
| `useAiChat` | `hooks/useAiChat.js` | SSE streaming hook |
| `ScadEditor` | `components/ScadEditor.jsx` | Monaco editor + AI toggle |
| `aiService` | `services/aiService.js` | API client for AI endpoints |
