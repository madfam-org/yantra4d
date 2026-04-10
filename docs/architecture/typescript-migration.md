# TypeScript Migration Strategy

## Current State

The studio app (`apps/studio`) originally had ~244 JS/JSX files with zero TypeScript annotations. As of April 2026, **49 files** have been migrated to TypeScript — all hooks, services, and library utilities are done (Phase 2 complete). Phase 3 (components + contexts) is next.

The admin app has ~15 JS/JSX files (migration deferred). The SDK package (`packages/sdk`) is already written in TypeScript and exports types consumed by the studio.

## TypeScript Configuration

`apps/studio/tsconfig.json` uses:

- `strict: true` — full strict checking is active and passing
- `allowJs: true` — `.js`/`.jsx` files can coexist with `.ts`/`.tsx`
- `checkJs: false` — JavaScript files are not type-checked (prevents errors in unmigrated JSX)
- `moduleResolution: "bundler"` — Vite-compatible resolution

This combination means: TypeScript files get full strict checking, while JavaScript files compile without type errors. No `// @ts-check` is needed.

## Migration Phases

### Phase 1: Enable TypeScript — COMPLETE

`tsconfig.json` added with `allowJs: true` and `strict: true`. `tsc --noEmit` passes with zero errors.

### Phase 2: Migrate Leaf Files — COMPLETE

All 49 leaf files migrated. Grouped by directory:

**`src/lib/` (12 files)**
| File | Key Types Added |
|------|----------------|
| `downloadUtils.ts` | `ZipUrlItem`, `ZipDataItem` interfaces |
| `slugUtils.ts` | `validateSlug` return type `string \| null` |
| `utils.ts` | `ClassValue` from clsx |
| `stl-utils.ts` | `ParsedSTL`, `BoundingBox` interfaces |
| `analytics.ts` | Event tracking types |
| `billing.ts` | Checkout URL generation types |
| `idleCallback.ts` | `requestIdleCallback` wrapper types |
| `monacoAiDiff.ts` | Monaco diff overlay types |
| `openscad-phases.ts` | Render phase detection types |
| `previewHintInference.ts` | Axis inference types |
| `printEstimator.ts` | Print estimation types |
| `scad-language.ts` | Monaco language definition |

**`src/services/` (8 files)**
| File | Key Types Added |
|------|----------------|
| `core/apiClient.ts` | `TokenGetter`, `RateLimitState`, `RateLimitListener` |
| `core/backendDetection.ts` | Boolean state, explicit return types |
| `core/websocketClient.ts` | WebSocket message types |
| `cache/renderCache.ts` | `CacheEntry`, `SerializedPart`, `CachedPart`, `PutPart` |
| `engine/renderService.ts` | `Manifest`, `ModeConfig`, `PartDef`, `RenderPart`, `RenderOptions`, `SSEData` |
| `domain/aiService.ts` | AI endpoint request/response types |
| `domain/assemblyFetcher.ts` | Assembly step types |
| `domain/editorService.ts` | SCAD file CRUD types |
| `domain/gitService.ts` | Git operation types |

**`src/hooks/` (26 files)**
| Directory | Files | Key Types |
|-----------|-------|-----------|
| `ai/` | `useAiChat.ts` | Chat state, SSE event types |
| `editor/` | `useUndoRedo.ts`, `useAssemblyEditor.ts`, `useAssemblyGuide.ts`, `useConstraints.ts`, `useEditorRender.ts`, `useKeyboardShortcuts.ts` | Editor state interfaces |
| `project/` | `useProjectActions.ts`, `useProjectMeta.ts`, `useProjectParams.ts`, `useShareableUrl.ts` | Project state, param types |
| `render/` | `useImageExport.ts`, `useParameterPreviewCache.ts`, `useRender.ts`, `useRenderQueue.ts`, `useWorkerLoader.ts` | Render state, worker types |
| `system/` | `useMediaQuery.ts`, `useUnitSystem.ts`, `useAnalytics.ts`, `useHashNavigation.ts`, `useLocalStoragePersistence.ts`, `usePanelLayout.ts`, `useThemeAndLanguage.ts`, `useTier.ts`, `useUpgradePrompt.ts` | System config types |

**Other (3 files)**
- `src/config/languages.ts` — Language configuration
- `src/components/ui/UpgradeModal.tsx` — Typed component (shadcn extension)
- `src/vite-env.d.ts` — Vite environment type definitions

All importing files use implicit extension resolution — no import path changes required.

### Phase 3: Components + Contexts — IN PROGRESS

Remaining files to migrate (not counting shadcn UI or test files):

| Category | Count | Notes |
|----------|-------|-------|
| Context providers (`src/contexts/`) | 10 | 9 JSX + 1 JS; typed contexts propagate to all consumers |
| Root files | 2 | `main.jsx`, `App.jsx` |
| Worker | 1 | `openscad-worker.js` (Web Worker, no JSX) |
| Components (non-shadcn) | ~76 | Across 11 subdirectories |
| **Total** | **~89** | |

**Do NOT migrate:** `src/components/ui/*.jsx` — these are shadcn primitives managed by the CLI.

Recommended migration order:
1. Worker file (pure logic, no JSX)
2. Context providers (typed contexts benefit entire app)
3. Root files (`main.jsx`, `App.jsx`)
4. Components in batches by directory

### Phase 4: Strict Mode — ALREADY ACTIVE

`strict: true` is already set and working. `checkJs: false` prevents strict checking of unmigrated `.jsx` files. Once all JSX files are converted to TSX, `checkJs` can be removed entirely.

## SDK Types

`@yantra4d/sdk` exports these types that can be consumed in migrated files:

- `YantraManifest` — Full project manifest type
- `YantraParameter` — Parameter definition
- `YantraMode` — Mode definition
- `YantraPart` — Part definition
- `YantraCartridge` — Self-contained project cartridge
- `RenderOptions` — Render API request

## Estimated Remaining Effort

- Phase 3 (components + contexts): 5-7 days across multiple PRs
- Phase 4 cleanup (remove `checkJs: false`): 1 hour after Phase 3

This is a multi-sprint effort and should not block feature work.
