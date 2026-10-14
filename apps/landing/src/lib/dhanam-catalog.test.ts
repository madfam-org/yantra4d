import { describe, expect, it, vi } from 'vitest';
import {
  DHANAM_CATALOG_URL,
  fetchMonthlyMxnPrice,
  formatMxnCentavos,
  monthlyMxnCentavos,
} from './dhanam-catalog';

const CATALOG = {
  slug: 'yantra4d',
  tiers: [
    { slug: 'creator', prices: {} },
    { slug: 'pro', prices: { MXN: { monthly: 59900, yearly: null } } },
    { slug: 'studio', prices: { MXN: { monthly: 299900, yearly: null } } },
  ],
};

describe('monthlyMxnCentavos', () => {
  it('reads the monthly MXN price of a tier', () => {
    expect(monthlyMxnCentavos(CATALOG, 'pro')).toBe(59900);
    expect(monthlyMxnCentavos(CATALOG, 'studio')).toBe(299900);
  });

  it('returns null for a free tier, an unknown tier or a malformed body', () => {
    expect(monthlyMxnCentavos(CATALOG, 'creator')).toBeNull();
    expect(monthlyMxnCentavos(CATALOG, 'madfam')).toBeNull();
    expect(monthlyMxnCentavos(null, 'pro')).toBeNull();
    expect(monthlyMxnCentavos({ tiers: 'nope' as unknown }, 'pro')).toBeNull();
  });
});

describe('formatMxnCentavos', () => {
  it('formats whole pesos', () => {
    expect(formatMxnCentavos(59900)).toBe('$599');
    expect(formatMxnCentavos(299900)).toBe('$2,999');
  });
});

describe('fetchMonthlyMxnPrice', () => {
  it('reads the public catalog and formats the price', async () => {
    const fetchImpl = vi.fn(
      async (_url: string, _init?: RequestInit) => new Response(JSON.stringify(CATALOG), { status: 200 }),
    );
    await expect(fetchMonthlyMxnPrice('pro', fetchImpl as unknown as typeof fetch)).resolves.toBe('$599');
    expect(fetchImpl.mock.calls[0][0]).toBe(DHANAM_CATALOG_URL);
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
