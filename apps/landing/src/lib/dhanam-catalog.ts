// Yantra4D's prices come from Dhanam's public catalog, the amounts Dhanam's
// checkout charges (owner rulings G1-1 and 2026-10-14). The landing is static,
// so Pricing.astro reads the catalog at build time. A failed read never falls
// back to a typed figure: the card then says the price is shown at checkout.
//
// The catalog lists each tier's MXN prices before IVA in `prices.MXN` and the
// IVA-inclusive amounts the checkout charges in the sibling `grossPrices.MXN`,
// rounded by a rule that lives in Dhanam (`ceil_whole_peso_iva`). Mexican
// consumer law (LFPC Art. 7 Bis) asks for the total price, taxes included, so
// the card shows the gross ("IVA incluido") and, while the catalog has no
// `grossPrices`, the net labelled "+ IVA", never a bare net figure. The gross
// is never computed here: the rounding rule stays in Dhanam.
export const DHANAM_CATALOG_URL = 'https://api.dhan.am/v1/billing/catalog/yantra4d';

export type CatalogPeriod = 'monthly' | 'yearly';

/** An amount to display, in MXN centavos. `ivaIncluded` false: the net, shown with "+ IVA". */
export interface DisplayPrice {
  amount: number;
  ivaIncluded: boolean;
}

/** A formatted display price, e.g. { text: '$695', ivaIncluded: true }. */
export interface FormattedPrice {
  text: string;
  ivaIncluded: boolean;
}

function asAmount(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : null;
}

/** The `MXN` entry of a `prices` or `grossPrices` block, if any. */
function mxnBlock(block: unknown): Record<string, unknown> | null {
  if (!block || typeof block !== 'object') return null;
  const mxn = (block as Record<string, unknown>).MXN;
  return mxn && typeof mxn === 'object' ? (mxn as Record<string, unknown>) : null;
}

/** Pick the amount to show for one period of a catalog tier. */
export function catalogDisplayPrice(tier: unknown, period: CatalogPeriod): DisplayPrice | null {
  if (!tier || typeof tier !== 'object') return null;
  const { prices, grossPrices } = tier as { prices?: unknown; grossPrices?: unknown };
  const net = asAmount(mxnBlock(prices)?.[period]);
  const gross = asAmount(mxnBlock(grossPrices)?.[period]);
  // A gross below the net is not a gross (wrong unit or field): show the net.
  if (gross !== null && (net === null || gross >= net)) return { amount: gross, ivaIncluded: true };
  if (net !== null) return { amount: net, ivaIncluded: false };
  return null;
}

/** Monthly display price of one catalog tier, or null when absent or free. */
export function monthlyDisplayPrice(body: unknown, tierSlug: string): DisplayPrice | null {
  const tiers = (body as { tiers?: unknown } | null)?.tiers;
  if (!Array.isArray(tiers)) return null;
  const tier = tiers.find((t) => (t as { slug?: unknown } | null)?.slug === tierSlug);
  return catalogDisplayPrice(tier, 'monthly');
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
): Promise<FormattedPrice | null> {
  try {
    const res = await fetchImpl(DHANAM_CATALOG_URL, { signal: AbortSignal.timeout(timeoutMs) });
    if (!res.ok) return null;
    const price = monthlyDisplayPrice(await res.json(), tierSlug);
    return price === null
      ? null
      : { text: formatMxnCentavos(price.amount), ivaIncluded: price.ivaIncluded };
  } catch {
    return null;
  }
}
