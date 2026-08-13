---
title: AI Assistant
description: Using natural language to adjust model parameters and edit SCAD code with AI.
---

Yantra4D includes two AI-powered features that let you interact with parametric models using natural language instead of manual slider adjustments.

## AI Configurator

**Tier required:** Essentials or higher

The AI Configurator lets you describe what you want in plain language, and the AI adjusts the model parameters for you.

### How to use it

1. Open the **AI Chat** panel in the studio sidebar.
2. Make sure the mode is set to **Configurator**.
3. Type a request describing the change you want.
4. The AI responds with an explanation of what it changed, and the sliders update automatically.

### Example requests

| What you type | What happens |
|---|---|
| "Make it wider and shorter" | Width increases, height decreases |
| "I need 6 slots instead of 4" | Slot count parameter updates to 6 |
| "Set everything to the minimum" | All sliders move to their minimum values |
| "Make it more compact for a small printer" | Multiple dimensions reduce proportionally |
| "Double the wall thickness" | Wall thickness parameter doubles (clamped to max) |

### How it works

Behind the scenes:

1. Your message is sent to the backend along with the current parameter values.
2. The backend builds a prompt that includes all parameter names, their types, current values, and valid ranges.
3. The LLM responds with an explanation and a set of parameter changes in JSON format.
4. The backend validates every suggested change against the manifest constraints:
   - Numeric values are clamped to `[min, max]`
   - Values are rounded to the nearest `step` increment
   - Unknown parameter IDs are silently dropped
   - Boolean parameters are explicitly converted
5. Validated changes stream back to the browser and apply to the sliders.

### Multi-turn conversations

The AI maintains conversation context within a session. You can refine your request across multiple messages:

> "Make it wider" --> "Actually, a bit less" --> "Now make it taller too"

Sessions expire after 1 hour of inactivity.

### Tips for better results

- **Be specific about dimensions.** "Make the width 80mm" works better than "make it bigger".
- **Reference parameter names.** If you know the parameter name (visible on the slider label), use it directly: "Set `num_slots` to 8".
- **Describe the goal.** "I need this to fit a 200mm print bed" gives the AI useful context.
- **One change at a time works too.** Simple requests like "increase height" are reliably interpreted.

### Limitations

- The AI can only adjust parameters that exist in the project manifest. It cannot add new parameters or change the model geometry beyond what the sliders allow.
- Suggested values are always clamped to the parameter's defined range. The AI cannot set a width to 200mm if the maximum is 100mm.
- The AI does not see the 3D model. It reasons about parameter names and ranges, not visual geometry.

## AI Code Editor

**Tier required:** Pro or higher

The AI Code Editor lets you describe changes to the underlying OpenSCAD source code in natural language. This is an advanced feature for users who want to modify the geometry itself, not just the parameter values.

### How to use it

1. Open the **SCAD Editor** panel in the studio.
2. Open one or more `.scad` files in the Monaco editor.
3. Toggle the **AI** button to enable the AI panel.
4. Describe the code change you want.
5. The AI generates search-and-replace edits that are applied to the open files.

### Example requests

| What you type | What happens |
|---|---|
| "Add rounded corners to the base" | AI generates SCAD code edits adding `rounding` parameters to the base geometry |
| "Replace the cube with a cylinder" | AI finds the `cube()` call and replaces it with an equivalent `cylinder()` |
| "Add a mounting hole on each corner" | AI inserts `difference()` and `cylinder()` calls for corner holes |

### How edits work

The AI produces edits using exact string matching (not line numbers) for robustness:

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

The backend validates each edit to ensure the target file exists and the search string is found before applying it. Edits are applied client-side in the Monaco editor, so you can review and undo them.

### Limitations

- The AI edits are applied to the files currently open in the editor. It cannot modify files that are not loaded.
- Complex multi-file refactors may require multiple turns of conversation.
- Always review generated edits before saving. The AI may produce syntactically valid SCAD that does not render as expected.

## Rate limits

AI requests are rate-limited per tier:

| Tier | Requests per hour |
|------|:---:|
| Guest | 0 |
| Essentials | 20 |
| Pro | 100 |
| Madfam | 300 |
