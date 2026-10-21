/**
 * Whether the visitor's tier can run the engine a mode renders with — asked
 * BEFORE the render, from what the Studio already knows (`/api/me` limits, or
 * `/api/tiers` for the tier), so a tier without the engine sees the upgrade
 * prompt instead of a long-render estimate followed by an HTTP 403.
 *
 * The server stays the authority (`render_orchestrator.resolve_engine_config`
 * answers 403 exactly as before). This only decides what to show first, so an
 * unknown answer (limits not loaded, a key the tier config does not carry) is
 * "allowed": the request goes out and the server decides.
 */
import { effectiveModeEngine, type ModeEngineManifest } from '../services/engine/renderPlacement'

/** Engines behind a tier feature flag in apps/api/tiers.json. Others are open to every tier. */
export const ENGINE_TIER_FEATURE: Readonly<Record<string, string>> = {
  cadquery: 'cadquery_engine',
  graph: 'graph_engine',
}

export interface EngineGate {
  allowed: boolean
  /** The engine the mode renders with (renderPlacement.effectiveModeEngine). */
  engine: string
  /** The tier feature that engine needs, or null when it needs none. */
  feature: string | null
}

/** PURE. The gate for one mode under `limits` (a tiers.json entry). */
export function engineGateFor(
  manifest: ModeEngineManifest | null | undefined,
  modeId: string | null | undefined,
  limits: Record<string, unknown> | null | undefined,
): EngineGate {
  const engine = effectiveModeEngine(manifest, modeId)
  const feature = ENGINE_TIER_FEATURE[engine] ?? null
  if (!feature || !limits || typeof limits[feature] !== 'boolean') {
    return { allowed: true, engine, feature }
  }
  return { allowed: limits[feature] === true, engine, feature }
}

/** PURE. Ids of the modes this tier can render, in manifest order. */
export function modesAllowedForTier(
  manifest: ModeEngineManifest | null | undefined,
  limits: Record<string, unknown> | null | undefined,
): string[] {
  return (manifest?.modes ?? [])
    .map(m => m?.id)
    .filter((id): id is string => typeof id === 'string' && engineGateFor(manifest, id, limits).allowed)
}
