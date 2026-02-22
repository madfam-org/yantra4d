"""
AI Synthesizer: Natural language -> Complete Yantra4D Cartridge (manifest + scad files)

Uses streaming LLM output to hallucinate a structurally complete openSCAD project
with the required project.json manifest bounds and CDG interfaces.
"""

import json
import logging
import re
from typing import Iterator

from services.ai.ai_provider import stream_chat
from services.ai.ai_session import append_message, get_messages

logger = logging.getLogger(__name__)

def build_synthesis_prompt() -> str:
    """Build system prompt for zero-shot Yantra4D Cartridge Generation."""
    return """You are the Yantra4D Synthesis Engine. 
You are tasked with generating a fully compliant parametric "Bounded 4D Hyperobject" (Cartridge) from a user script.

A Yantra4D Cartridge requires two components:
1. `project.json` (The manifest dictating parameters, UI modes, logic limits).
2. OpenSCAD code files.

When the user gives a description, respond with a JSON block containing the generated Cartridge:

Your brief technical explanation string here...

```json
{
  "slug": "url-safe-project-slug-here",
  "manifest": {
    "project": {"name": "User Friendly Title", "slug": "slug-match", "version": "1.0.0"},
    "modes": [{"id": "main", "scad_file": "main.scad", "parts": ["part1"]}],
    "parts": [{"id": "part1", "render_mode": 0, "default_color": "#e5e7eb"}],
    "parameters": [{"id": "size", "type": "slider", "min": 1, "max": 100, "default": 20}]
  },
  "files": {
    "main.scad": "size = 20;\\ncube(size);"
  }
}
```

Rules:
- You must output VALID JSON. Escape newlines properly in the SCAD file payload!
- Use OpenSCAD best practices.
- Ensure the `$fn` variable logic is hooked up if your code has curves.
- Keep explanations outside the JSON extremely concise."""

def parse_synthesis(raw: str) -> dict:
    """Extract and validate the hallucinated Cartridge."""
    json_match = re.search(r"```json\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if not json_match:
        json_match = re.search(r"\{[^{}]*\"manifest\"\s*:\s*\{.*?\}\s*\}", raw, re.DOTALL)
        
    if not json_match:
        return {"explanation": raw, "cartridge": None}

    try:
        data = json.loads(json_match.group(1) if "```" in raw else json_match.group(0))
        
        # Verify mandatory keys exist structurally
        if "slug" not in data or "manifest" not in data or "files" not in data:
            return {"explanation": raw, "cartridge": None}
            
        validated = {
            "slug": data["slug"],
            "manifest": data["manifest"],
            "files": data["files"]
        }
    except json.JSONDecodeError:
        return {"explanation": raw, "cartridge": None}

    explanation = re.sub(r"```json\s*\n?.*?\n?```", "", raw, flags=re.DOTALL).strip()
    return {"explanation": explanation, "cartridge": validated}

def stream_synthesis_response(session_id: str, message: str) -> Iterator[dict]:
    """Yield SSE events for project synthesis."""
    system = build_synthesis_prompt()
    append_message(session_id, "user", message)
    messages = get_messages(session_id)

    full_text = ""
    for chunk in stream_chat(messages, system=system):
        full_text += chunk
        yield {"event": "chunk", "text": chunk}

    append_message(session_id, "assistant", full_text)

    parsed = parse_synthesis(full_text)
    if parsed["cartridge"]:
        # Save to disk to create the Yantra4D Cartridge structure
        cartridge = parsed["cartridge"]
        slug = cartridge["slug"]
        manifest = cartridge["manifest"]
        files = cartridge["files"]
        
        from config import Config
        from pathlib import Path
        projects_dir = Path(Config.PROJECTS_DIR)
        
        new_project_dir = projects_dir / slug
        if new_project_dir.exists():
            # append salt to avoid overwriting existing projects
            import uuid
            slug = f"{slug}-{str(uuid.uuid4())[:4]}"
            new_project_dir = projects_dir / slug
            
        new_project_dir.mkdir(parents=True, exist_ok=True)
        
        # Write project.json
        manifest_path = new_project_dir / "project.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
            
        # Write OpenSCAD files
        for filename, content in files.items():
            file_path = new_project_dir / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Notify UI of success and the slug to redirect to
        yield {"event": "cartridge", "cartridge": cartridge, "slug": slug}

    yield {"event": "done"}
