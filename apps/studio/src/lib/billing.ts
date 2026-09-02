/**
 * Dhanam billing integration for Yantra4D.
 *
 * Provides checkout URL generation for tier upgrades.
 */
import { tierAtLeast } from './tiers';

// Defaults to the canonical Dhanam web checkout. The fallback domain
// (billing.yantra4d.com) was never provisioned and resulted in a DNS
// failure when VITE_DHANAM_CHECKOUT_URL was unset. Dhanam's checkout
// page accepts the same query-param shape this module produces.
const DHANAM_CHECKOUT_URL =
  import.meta.env.VITE_DHANAM_CHECKOUT_URL || 'https://app.dhan.am/checkout';

export type { TierName as Yantra4DTier } from './tiers';

/** The tiers a customer can buy. `guest` and `essentials` are not sold. */
type PaidTier = 'pro' | 'premium';

/**
 * Paid tier -> the checkout plan id Dhanam has registered for it.
 *
 * An explicit table, never `yantra4d_${tier}`. Two reasons, both from ADR-006:
 * the plan id and the tier name are different namespaces (Decision 5 — writing
 * a plan id into the `yantra4d_tier` claim seats a paying customer in
 * essentials with no error anywhere), and the top tier's SKU is still
 * `yantra4d_madfam` because the SKU slug lives in tulana's catalog and was not
 * part of the `madfam` -> `premium` tier rename. Deriving one from the other
 * would have silently pointed checkout at a plan that does not exist.
 */
const CHECKOUT_PLAN_IDS: Record<PaidTier, string> = {
  pro: 'yantra4d_pro',
  premium: 'yantra4d_madfam',
};

/**
 * Build a checkout URL for upgrading to a Yantra4D tier via Dhanam.
 */
export function getCheckoutUrl(
  plan: PaidTier = 'pro',
  userId?: string,
  returnUrl?: string,
): string {
  const params = new URLSearchParams({
    plan: CHECKOUT_PLAN_IDS[plan],
    product: 'yantra4d',
  });
  if (userId) params.set('user_id', userId);
  if (returnUrl) params.set('return_url', returnUrl);
  return `${DHANAM_CHECKOUT_URL}?${params.toString()}`;
}

/**
 * Check if a tier has access to premium features.
 *
 * Accepts the deprecated `madfam` name as well as `premium`.
 */
export function isPremiumTier(tier: string): boolean {
  return tierAtLeast(tier, 'pro');
}
