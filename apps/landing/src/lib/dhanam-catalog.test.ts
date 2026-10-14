import { describe, expect, it, vi } from 'vitest';
import {
  DHANAM_CATALOG_URL,
  catalogDisplayPrice,
  fetchMonthlyMxnPrice,
  formatMxnCentavos,
  monthlyDisplayPrice,
} from './dhanam-catalog';

// The catalog as Dhanam served it before `grossPrices` (net prices only).
const CATALOG = {
  slug: 'yantra4d',
  tiers: [
    { slug: 'creator', prices: {} },
    { slug: 'pro', prices: { MXN: { monthly: 59900, yearly: null } } },
    { slug: 'studio', prices: { MXN: { monthly: 299900, yearly: null } } },
  ],
};

// The same catalog once Dhanam sends `grossPrices` next to `prices`: the
// IVA-inclusive amounts its checkout charges (rule owned by Dhanam).
const CATALOG_WITH_GROSS = {
  slug: 'yantra4d',
  tiers: [
    { slug: 'creator', prices: {}, grossPrices: {} },
    {
      slug: 'pro',
      prices: { MXN: { monthly: 59900, yearly: null } },
      grossPrices: {
        MXN: { monthly: 69500, yearly: null, ivaRate: 0.16, pricingRule: 'ceil_whole_peso_iva' },
      },
    },
  ],
};

describe('catalogDisplayPrice', () => {
  it('shows grossPrices.MXN, IVA included, when the catalog sends it', () => {
    expect(catalogDisplayPrice(CATALOG_WITH_GROSS.tiers[1], 'monthly')).toEqual({
      amount: 69500,
      ivaIncluded: true,
    });
  });

  it('falls back to the net, marked as before IVA, when grossPrices is absent', () => {
    expect(catalogDisplayPrice(CATALOG.tiers[1], 'monthly')).toEqual({
      amount: 59900,
      ivaIncluded: false,
    });
  });

  it('falls back to the net when the gross for that interval is null', () => {
    const tier = { prices: { MXN: { monthly: 59900 } }, grossPrices: { MXN: { monthly: null } } };
    expect(catalogDisplayPrice(tier, 'monthly')).toEqual({ amount: 59900, ivaIncluded: false });
  });

  it('never computes a gross from the net (the rounding rule stays in Dhanam)', () => {
    const tier = { prices: { MXN: { monthly: 59900 } }, grossPrices: {} };
    expect(catalogDisplayPrice(tier, 'monthly')?.amount).toBe(59900);
  });

  it('ignores a gross below the net (wrong unit or field)', () => {
    const tier = { prices: { MXN: { monthly: 59900 } }, grossPrices: { MXN: { monthly: 695 } } };
    expect(catalogDisplayPrice(tier, 'monthly')).toEqual({ amount: 59900, ivaIncluded: false });
  });

  it('returns null for free, unpriced and USD-only tiers', () => {
    expect(catalogDisplayPrice({ prices: {}, grossPrices: {} }, 'monthly')).toBeNull();
    expect(catalogDisplayPrice({ prices: { USD: { monthly: 1999 } } }, 'monthly')).toBeNull();
    expect(catalogDisplayPrice(null, 'monthly')).toBeNull();
  });
});

describe('monthlyDisplayPrice', () => {
  it('reads the monthly price of a tier', () => {
    expect(monthlyDisplayPrice(CATALOG, 'pro')).toEqual({ amount: 59900, ivaIncluded: false });
    expect(monthlyDisplayPrice(CATALOG_WITH_GROSS, 'pro')).toEqual({
      amount: 69500,
      ivaIncluded: true,
    });
  });

  it('returns null for a free tier, an unknown tier or a malformed body', () => {
    expect(monthlyDisplayPrice(CATALOG, 'creator')).toBeNull();
    expect(monthlyDisplayPrice(CATALOG, 'madfam')).toBeNull();
    expect(monthlyDisplayPrice(null, 'pro')).toBeNull();
    expect(monthlyDisplayPrice({ tiers: 'nope' as unknown }, 'pro')).toBeNull();
  });
});

describe('formatMxnCentavos', () => {
  it('formats whole pesos', () => {
    expect(formatMxnCentavos(59900)).toBe('$599');
    expect(formatMxnCentavos(299900)).toBe('$2,999');
  });
});

describe('fetchMonthlyMxnPrice', () => {
  it('reads the public catalog and formats the net, flagged as before IVA', async () => {
    const fetchImpl = vi.fn(
      async (_url: string, _init?: RequestInit) => new Response(JSON.stringify(CATALOG), { status: 200 }),
    );
    await expect(fetchMonthlyMxnPrice('pro', fetchImpl as unknown as typeof fetch)).resolves.toEqual({
      text: '$599',
      ivaIncluded: false,
    });
    expect(fetchImpl.mock.calls[0][0]).toBe(DHANAM_CATALOG_URL);
  });

  it('formats the IVA-inclusive gross when the catalog sends it', async () => {
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify(CATALOG_WITH_GROSS), { status: 200 }));
    await expect(fetchMonthlyMxnPrice('pro', fetchImpl as unknown as typeof fetch)).resolves.toEqual({
      text: '$695',
      ivaIncluded: true,
    });
  });

  it('never invents a price: an error, a non-200 or a missing tier is null', async () => {
    const down = vi.fn(async () => {
      throw new Error('offline');
    });
    const notOk = vi.fn(async () => new Response('x', { status: 503 }));
    const ok = vi.fn(async () => new Response(JSON.stringify(CATALOG), { status: 200 }));
    await expect(fetchMonthlyMxnPrice('pro', down as unknown as typeof fetch)).resolves.toBeNull();
    await expect(fetchMonthlyMxnPrice('pro', notOk as unknown as typeof fetch)).resolves.toBeNull();
    await expect(fetchMonthlyMxnPrice('madfam', ok as unknown as typeof fetch)).resolves.toBeNull();
  });
});
