"""
AI Code Editor: Natural language → SCAD code edits.

Uses search/replace for content-addressed editing robust to multi-turn changes.
"""
import json
import logging
import re
from typing import Iterator

from services.ai.ai_provider import stream_chat
from services.ai.ai_session import append_message, get_messages

logger = logging.getLogger(__name__)


def build_code_editor_prompt(manifest: dict, file_contents: dict[str, str]) -> str:
    """Build system prompt with manifest context and all SCAD file contents."""
    files_text = ""
    for fname, content in file_contents.items():
        files_text += f"\n--- {fname} ---\n{content}\n"

    project_name = manifest.get("project", {}).get("name", "Unknown")

    params_desc = []
    for p in manifest.get("parameters", []):
        params_desc.append(f"- ${p['id']}: {p.get('label', p['id'])} ({p.get('type', 'number')})")
    params_text = "\n".join(params_desc) if params_desc else "(no parameters)"

    return f"""You are an AI assistant that modifies OpenSCAD code for a parametric 3D model: "{project_name}".

Parameters defined in the manifest:
{params_text}

Current SCAD files:
{files_text}

When the user asks for code changes, respond with a JSON block containing search/replace edits AND an explanation.
Format your response as natural text with an embedded JSON block:

Your explanation here...

```json
{{"edits": [{{"file": "filename.scad", "search": "exact old code", "replace": "new code"}}]}}
```

Rules:
- Use exact string matching for "search" — copy the code precisely from the files above
- Keep edits minimal and focused
- Preserve OpenSCAD conventions: snake_case, $variables for parameters
- If adding new geometry, ensure it integrates with existing render_mode logic
- If the request is unclear, explain what you'd change and why before providing edits
- Keep explanations concise"""


def parse_edits(raw: str, file_contents: dict[str, str]) -> dict:
    """Extract and validate edits from LLM response."""
    json_match = re.search(r"```json\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if not json_match:
        json_match = re.search(r"\{[^{}]*\"edits\"\s*:\s*\[.*?\]\s*\}", raw, re.DOTALL)
    if not json_match:
        return {"explanation": raw, "edits": []}

    try:
        data = json.loads(json_match.group(1) if "```" in raw else json_match.group(0))
    except json.JSONDecodeError:
        return {"explanation": raw, "edits": []}

    edits = data.get("edits", [])
    validated = []
    for edit in edits:
        fname = edit.get("file", "")
        search = edit.get("search", "")
        replace = edit.get("replace", "")
        if fname not in file_contents:
            continue
        if search and search in file_contents[fname]:
            validated.append({"file": fname, "search": search, "replace": replace})

    explanation = re.sub(r"```json\s*\n?.*?\n?```", "", raw, flags=re.DOTALL).strip()
    return {"explanation": explanation, "edits": validated}


def stream_response(session_id: str, message: str, manifest: dict, file_contents: dict[str, str]) -> Iterator[dict]:
    """Yield SSE events: chunk (text), edits (validated), done."""
    system = build_code_editor_prompt(manifest, file_contents)
    append_message(session_id, "user", message)
    messages = get_messages(session_id)

    full_text = ""
    for chunk in stream_chat(messages, system=system):
        full_text += chunk
        yield {"event": "chunk", "text": chunk}

    append_message(session_id, "assistant", full_text)

    parsed = parse_edits(full_text, file_contents)
    if parsed["edits"]:
        yield {"event": "edits", "edits": parsed["edits"]}

    yield {"event": "done"}
