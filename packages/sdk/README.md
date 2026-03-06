# @yantra4d/sdk

Headless SDK for rendering Yantra4D Cartridges (parametric 3D print designs).

## Installation

```bash
npm install @yantra4d/sdk
```

## Usage

```typescript
import { YantraEngine } from '@yantra4d/sdk'
import type { YantraCartridge } from '@yantra4d/sdk'

// Initialize engine pointing at a Yantra4D API backend
const engine = new YantraEngine({ apiBase: 'https://4d-api.madfam.io' })

// Load a cartridge (project manifest)
const cartridge: YantraCartridge = {
  manifest: await fetch('https://4d-api.madfam.io/api/projects/gridfinity/manifest').then(r => r.json())
}

// Get default parameter values
const defaults = engine.getDefaultParams(cartridge)
// { grid_x: 2, grid_y: 2, ... }

// Validate parameters against constraints
const violations = engine.evaluateConstraints(cartridge, { grid_x: 100 })
// { grid_x: ['Value must be <= 10'] }

// Render a model
const result = await engine.render(cartridge, {
  mode: 'baseplate',
  params: { grid_x: 3, grid_y: 3 },
  parts: ['baseplate'],
})
console.log(result.url) // URL to the rendered GLB file
```

## API

### `YantraEngine`

#### `constructor(options: { apiBase: string })`

Create an engine instance pointing at a Yantra4D API backend.

#### `getDefaultParams(cartridge): Record<string, any>`

Extract default values from all parameters in the manifest.

#### `evaluateConstraints(cartridge, params): Record<string, string[]>`

Validate parameters against min/max constraints. Returns a map of parameter ID to violation messages.

#### `render(cartridge, options): Promise<RenderResult>`

Request a server-side render. Returns `{ url, logs }`.

## Types

- `YantraManifest` — Full project manifest
- `YantraParameter` — Parameter definition (slider, select, boolean, etc.)
- `YantraMode` — Mode definition (SCAD file, parts, estimate)
- `YantraPart` — Part definition (render mode, color)
- `YantraCartridge` — Self-contained project bundle (manifest + optional asset loaders)
- `RenderOptions` — Render request options (mode, params, parts, colors)
- `RenderResult` — Render response (url, logs)

## License

AGPL-3.0
