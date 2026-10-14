// Yantra4D's prices come from Dhanam's public catalog, the amounts Dhanam's
// checkout charges (owner rulings G1-1 and 2026-10-14). The landing is static,
// so Pricing.astro reads the catalog at build time. A failed read never falls
// back to a typed figure: the card then says the price is shown at checkout.
export const DHANAM_CATALOG_URL = 'https://api.dhan.am/v1/billing/catalog/yantra4d';

type CatalogBody = {
  tiers?: Array<{ slug?: string; prices?: { MXN?: { monthly?: number | null } } }>;
};

/** Monthly MXN price in centavos for one catalog tier, or null when absent. */
export function monthlyMxnCentavos(body: unknown, tierSlug: string): number | null {
  const tiers = (body as CatalogBody | null)?.tiers;
  if (!Array.isArray(tiers)) return null;
  const monthly = tiers.find((t) => t?.slug === tierSlug)?.prices?.MXN?.monthly;
  return typeof monthly === 'number' && Number.isFinite(monthly) && monthly > 0 ? monthly : null;
}

/** Format MXN centavos as whole pesos, e.g. 59900 -> "$599". */
export function formatMxnCentavos(centavos: number): string {
  return `$${Math.round(centavos / 100).toLocaleString('en-US')}`;
}

/** Build-time read of one tier's monthly price, formatted; null on any failure. */
export async function fetchMonthlyMxnPrice(
  tierSlug: string,
  fetchImpl: typeof fetch = fetch,
  timeoutMs = 8000,
): Promise<string | null> {
  try {
    const res = await fetchImpl(DHANAM_CATALOG_URL, { signal: AbortSignal.timeout(timeoutMs) });
    if (!res.ok) return null;
    const centavos = monthlyMxnCentavos(await res.json(), tierSlug);
    return centavos === null ? null : formatMxnCentavos(centavos);
  } catch {
    return null;
  }
}
