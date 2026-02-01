# Multi-Project Platform Guide

Qubic supports serving multiple parametric 3D projects from a single instance.

## Directory Structure

```
projects/
  tablaco/              # Flagship project (interlocking cubes)
    project.json
    *.scad
  gridfinity/           # Modular storage bins
    project.json
    *.scad
  polydice/             # Parametric dice set
    project.json
    *.scad
  ...                   # 15 built-in projects total
  my-custom-project/    # Onboarded project
    project.json
    *.scad
scad -> projects/tablaco/   # Backward-compat symlink
```

## Configuration

| Env Var | Default | Purpose |
|---------|---------|---------|
| `PROJECTS_DIR` | `projects/` (repo root) | Directory containing project subdirectories |
| `SCAD_DIR` | `scad/` (repo root) | Single-project fallback (used when no `PROJECTS_DIR`) |
| `LIBS_DIR` | `libs/` (repo root) | Global OpenSCAD library directory |
| `OPENSCADPATH` | value of `LIBS_DIR` | Library search path for OpenSCAD subprocesses |

**Mode detection**: If `PROJECTS_DIR` exists and contains subdirectories with `project.json`, multi-project mode activates. Otherwise, falls back to `SCAD_DIR`.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all discovered projects |
| GET | `/api/projects/{slug}/manifest` | Full manifest for a project |
| GET | `/api/manifest` | Default project manifest (backward compat) |
| POST | `/api/projects/analyze` | Upload `.scad` files, get analysis + draft manifest |
| POST | `/api/projects/create` | Save a new project to `PROJECTS_DIR` |

Render, verify, and estimate endpoints accept an optional `project` field in the JSON payload to scope operations to a specific project.

## Frontend

- **URL hash**: `#/{projectSlug}/{presetId}/{modeId}` (3-segment)
- **Backward compat**: 2-segment hash `#/{presetId}/{modeId}` still works (uses default project)
- **Project selector**: Dropdown appears in header when multiple projects are available
- **Per-project localStorage**: Parameters stored as `{slug}-params`, `{slug}-colors`, etc.

## Onboarding External Projects

### CLI

```bash
# Analyze without writing
scripts/qubic-init ./path/to/scad --slug my-project --analyze-only

# Generate manifest and install
scripts/qubic-init ./path/to/scad --slug my-project --install
```

### Web UI

1. Navigate to the onboarding wizard
2. Upload `.scad` files
3. Review auto-detected variables, modules, and render modes
4. Edit the generated manifest (parameter ranges, labels, modes)
5. Save — project appears in the project selector

## Docker

```yaml
backend:
  volumes:
    - ./projects:/app/projects:ro
  environment:
    - PROJECTS_DIR=/app/projects
```

## Adding a Project Manually

1. Create `projects/{slug}/`
2. Add `.scad` files
3. Create `project.json` following the [manifest schema](manifest.md)
4. Restart backend (or manifests are loaded on first request)
