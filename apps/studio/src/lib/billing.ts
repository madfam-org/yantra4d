/**
 * Dhanam billing integration for Yantra4D.
 *
 * Provides checkout URL generation for tier upgrades.
 */

// Defaults to the canonical Dhanam web checkout. The fallback domain
// (billing.yantra4d.com) was never provisioned and resulted in a DNS
// failure when VITE_DHANAM_CHECKOUT_URL was unset. Dhanam's checkout
// page accepts the same query-param shape this module produces.
const DHANAM_CHECKOUT_URL =
  import.meta.env.VITE_DHANAM_CHECKOUT_URL || 'https://app.dhan.am/checkout';

export type Yantra4DTier = 'guest' | 'essentials' | 'pro' | 'madfam';

/**
 * Build a checkout URL for upgrading to a Yantra4D tier via Dhanam.
 */
export function getCheckoutUrl(
  plan: 'pro' | 'madfam' = 'pro',
  userId?: string,
  returnUrl?: string,
): string {
  const params = new URLSearchParams({
    plan: `yantra4d_${plan}`,
    product: 'yantra4d',
  });
  if (userId) params.set('user_id', userId);
  if (returnUrl) params.set('return_url', returnUrl);
  return `${DHANAM_CHECKOUT_URL}?${params.toString()}`;
}

/**
 * Check if a tier has access to premium features.
 */
export function isPremiumTier(tier: Yantra4DTier): boolean {
  return tier === 'pro' || tier === 'madfam';
}
