# TypeScript Migration Strategy

## Current State

The studio app (`apps/studio`) has ~244 JS/JSX files with zero TypeScript type annotations. The admin app has ~15 JS/JSX files. Both use Vite which supports TypeScript out of the box.

The SDK package (`packages/sdk`) is already written in TypeScript and exports types that could be consumed immediately.

## Recommended Approach: Gradual Adoption

### Phase 1: Enable TypeScript Alongside JavaScript

1. Add `tsconfig.json` to `apps/studio/` with `allowJs: true` and `strict: false`
2. Add `// @ts-check` to leaf files as they're touched
3. No existing files need to be renamed — `.js`/`.jsx` files work as-is

### Phase 2: Migrate Leaf Files First

Priority order (least dependencies, most benefit from types):

1. **`src/lib/`** — Utility functions, API boundaries (`billing.ts` already exists as reference)
2. **`src/services/`** — `renderService.js`, `verifyService.js` (API response types)
3. **`src/hooks/`** — Custom hooks with clear input/output contracts
4. **`src/contexts/`** — Provider types propagate to all consumers

### Phase 3: Components (Last)

Components benefit least from TypeScript initially since props are validated at runtime by React. Migrate these last, starting with complex ones (Controls, Viewer, ScadEditor).

### Phase 4: Strict Mode

Once >80% of files are TypeScript, enable `strict: true` in `tsconfig.json`.

## SDK Types

`@yantra4d/sdk` exports these types that can be consumed immediately:

- `YantraManifest` — Full project manifest type
- `YantraParameter` — Parameter definition
- `YantraMode` — Mode definition
- `YantraPart` — Part definition
- `YantraCartridge` — Self-contained project cartridge
- `RenderOptions` — Render API request

## Estimated Effort

- Phase 1: 1 hour (config only)
- Phase 2: 2-3 days (services + hooks, ~30 files)
- Phase 3: 1-2 weeks (components, ~200 files)
- Phase 4: 1 day (config change + fix strict errors)

This is a multi-sprint effort and should not block feature work.

## Progress

### Wave 1 — Config (Phase 1)

Completed. `tsconfig.json` added to `apps/studio/` with `allowJs: true`, `strict: false`, `moduleResolution: "bundler"`.

### Wave 2 — Leaf Files (Phase 2, partial)

Eight leaf utility and service files migrated from `.js` to `.ts`:

| File | Key Types Added |
|------|----------------|
| `src/lib/downloadUtils.ts` | `ZipUrlItem`, `ZipDataItem` interfaces |
| `src/lib/slugUtils.ts` | `validateSlug` return type `string \| null` |
| `src/lib/utils.ts` | `ClassValue` from clsx |
| `src/lib/stl-utils.ts` | `ParsedSTL`, `BoundingBox` interfaces |
| `src/services/core/apiClient.ts` | `TokenGetter`, `RateLimitState`, `RateLimitListener` types |
| `src/services/core/backendDetection.ts` | `boolean \| null` state, explicit return types |
| `src/services/cache/renderCache.ts` | `CacheEntry`, `SerializedPart`, `CachedPart`, `PutPart` interfaces |
| `src/services/engine/renderService.ts` | `Manifest`, `ModeConfig`, `PartDef`, `EstimateConstants`, `ProgressEvent`, `RenderPart`, `RenderOptions`, `SSEData` interfaces |

All 43 importing files use implicit extension resolution — no import path changes required. `tsc --noEmit` passes with zero errors.

**Remaining Phase 2 candidates** (~22 more files): hooks (`src/hooks/`), remaining services (`verifyService.js`, `aiService.js`, etc.), and remaining lib files (`printEstimator.js`, `openscad-phases.js`).
