import pytest
import tempfile
from pathlib import Path
from config import Config
from services.ai.ai_synthesizer import parse_synthesis

@pytest.fixture
def mock_projects_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        monkeypatch.setattr(Config, "PROJECTS_DIR", temp_dir)
        yield Path(temp_dir)

def test_synthesis_parsing_and_extraction():
    # Mock LLM Output
    llm_response = '''
Here is your new Cartridge.

```json
{
  "slug": "test-synthesized-box",
  "manifest": {
    "project": {
      "name": "Test Box",
      "slug": "test-synthesized-box",
      "version": "1.0.0"
    },
    "modes": [
      {
        "id": "main",
        "scad_file": "main.scad",
        "parts": ["box"]
      }
    ],
    "parts": [
      {
        "id": "box",
        "render_mode": 0,
        "default_color": "#ff0000"
      }
    ],
    "parameters": [
      {
        "id": "width",
        "type": "slider",
        "min": 10,
        "max": 100,
        "default": 50
      }
    ]
  },
  "files": {
    "main.scad": "width=50;\\ncube([width, width, width]);"
  }
}
```
'''
    parsed = parse_synthesis(llm_response)
    
    assert parsed["cartridge"] is not None
    assert parsed["cartridge"]["slug"] == "test-synthesized-box"
    assert "width" in parsed["cartridge"]["files"]["main.scad"]
    assert len(parsed["cartridge"]["manifest"]["parameters"]) == 1

def test_invalid_json_is_caught():
    llm_response = '''
I made a box but forgot the JSON block!
{"slug": "test"
    '''
    parsed = parse_synthesis(llm_response)
    assert parsed["cartridge"] is None
