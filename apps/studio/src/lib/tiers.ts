/**
 * The Yantra4D tier ladder, client-side.
 *
 * Mirrors `apps/api/services/core/tier_service.py`. The API is the source of
 * truth — it normalises every tier it emits — but the Studio still compares
 * tier names locally (gating a button, ranking a requirement), so it needs the
 * same ladder and the same aliases.
 *
 * ADR-006 Decision 4 renamed the top tier `madfam` -> `premium`. The old name
 * is accepted **permanently**, not through a migration window: a cached
 * `/api/me` response, an old service worker, or a self-hosted backend running
 * an older image can all still say `madfam`, and a Studio that did not know
 * the word would quietly gate a paying user out of features they hold.
 *
 * Every hard-coded tier comparison in the Studio goes through `tierAtLeast`
 * so there is exactly one place that knows the ladder.
 */

export const TIER_HIERARCHY: Record<string, number> = {
  guest: 0,
  essentials: 1,
  pro: 2,
  premium: 3,
}

/** Deprecated tier name -> canonical name. Nothing is ever removed from this. */
export const LEGACY_TIER_ALIASES: Record<string, string> = {
  basic: 'essentials',
  madfam: 'premium',
}

export type TierName = 'guest' | 'essentials' | 'pro' | 'premium'

/** The most privileged tier, derived from the ladder rather than spelled out. */
export const TOP_TIER: TierName = 'premium'

/** Canonical name for a tier, mapping deprecated names forward. */
export function normalizeTier(tier: string | null | undefined): string {
  if (!tier) return ''
  return LEGACY_TIER_ALIASES[tier] ?? tier
}

/** Ladder position of a tier; unknown names sit at the bottom (fail closed). */
export function tierRank(tier: string | null | undefined): number {
  return TIER_HIERARCHY[normalizeTier(tier)] ?? 0
}

/** Whether `tier` meets or exceeds `required`. Both sides accept aliases. */
export function tierAtLeast(
  tier: string | null | undefined,
  required: string | null | undefined,
): boolean {
  return tierRank(tier) >= tierRank(required)
}

/** i18n key for a tier's display name, e.g. `tier.name_premium`. */
export function tierNameKey(tier: string | null | undefined): string {
  return `tier.name_${normalizeTier(tier) || 'guest'}`
}
