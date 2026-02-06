"""
AI Configurator: Natural language → parameter changes.

Maps user intent to manifest parameter adjustments with validation.
"""
import json
import logging
import re
from typing import Iterator

from services.ai_provider import stream_chat
from services.ai_session import append_message, get_messages

logger = logging.getLogger(__name__)


def build_configurator_prompt(manifest: dict, current_params: dict) -> str:
    """Build system prompt with all parameter context."""
    params_desc = []
    for p in manifest.get("parameters", []):
        desc = f"- {p['id']}: {p.get('label', p['id'])} (type={p.get('type', 'number')}"
        if "min" in p:
            desc += f", min={p['min']}"
        if "max" in p:
            desc += f", max={p['max']}"
        if "step" in p:
            desc += f", step={p['step']}"
        if "default" in p:
            desc += f", default={p['default']}"
        desc += f", current={current_params.get(p['id'], p.get('default', 0))})"
        if p.get("description"):
            desc += f" — {p['description']}"
        params_desc.append(desc)

    params_text = "\n".join(params_desc) if params_desc else "(no parameters)"

    return f"""You are an AI assistant for a parametric 3D design tool called Yantra4D.
The user is adjusting parameters on a 3D model: "{manifest.get('project', {}).get('name', 'Unknown')}".

Available parameters:
{params_text}

When the user asks to change the model, respond with a JSON block containing parameter changes AND a brief explanation.
Format your response as natural text with an embedded JSON block:

Your explanation here...

```json
{{"parameter_changes": {{"param_id": new_value, ...}}}}
```

Rules:
- Only set parameters that exist in the list above
- Respect min/max/step constraints
- If the user's request is ambiguous, make reasonable assumptions and explain them
- For preset-like requests ("make it for iPhone 15"), set ALL relevant parameters at once
- Keep explanations concise (1-3 sentences)
- If no parameter changes are needed, omit the JSON block"""


def build_preset_prompt(manifest: dict) -> str:
    """Variant prompt for NL preset generation."""
    return build_configurator_prompt(manifest, {}) + """

The user wants to generate a complete preset. Respond with ALL parameter values:

```json
{"preset_values": {"param_id": value, ...}, "preset_name": "Descriptive Name"}
```"""


def parse_response(raw: str, manifest: dict) -> dict:
    """Extract JSON from response, validate param IDs, clamp values."""
    # Find JSON block in markdown code fence or raw JSON
    json_match = re.search(r"```json\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if not json_match:
        json_match = re.search(r"\{[^{}]*\"parameter_changes\"[^{}]*\}", raw, re.DOTALL)
        if not json_match:
            json_match = re.search(r"\{[^{}]*\"preset_values\"[^{}]*\}", raw, re.DOTALL)
    if not json_match:
        return {"explanation": raw, "parameter_changes": {}}

    try:
        data = json.loads(json_match.group(1) if "```" in raw else json_match.group(0))
    except json.JSONDecodeError:
        return {"explanation": raw, "parameter_changes": {}}

    changes = data.get("parameter_changes") or data.get("preset_values") or {}

    # Build param lookup
    param_map = {p["id"]: p for p in manifest.get("parameters", [])}

    validated = {}
    for pid, val in changes.items():
        if pid not in param_map:
            continue
        p = param_map[pid]
        if p.get("type") == "boolean":
            validated[pid] = bool(val)
            continue
        try:
            val = float(val)
        except (TypeError, ValueError):
            continue
        if "min" in p:
            val = max(val, p["min"])
        if "max" in p:
            val = min(val, p["max"])
        if "step" in p and p["step"] > 0:
            base = p.get("min", 0)
            val = base + round((val - base) / p["step"]) * p["step"]
        validated[pid] = val

    # Remove JSON block from explanation
    explanation = re.sub(r"```json\s*\n?.*?\n?```", "", raw, flags=re.DOTALL).strip()

    result = {"explanation": explanation, "parameter_changes": validated}
    if "preset_name" in data:
        result["preset_name"] = data["preset_name"]
    return result


def stream_response(session_id: str, message: str, manifest: dict, current_params: dict) -> Iterator[dict]:
    """Yield SSE events: chunk (text), params (validated changes), done."""
    system = build_configurator_prompt(manifest, current_params)
    append_message(session_id, "user", message)
    messages = get_messages(session_id)

    full_text = ""
    for chunk in stream_chat(messages, system=system):
        full_text += chunk
        yield {"event": "chunk", "text": chunk}

    append_message(session_id, "assistant", full_text)

    parsed = parse_response(full_text, manifest)
    if parsed["parameter_changes"]:
        yield {"event": "params", "changes": parsed["parameter_changes"]}

    yield {"event": "done"}
