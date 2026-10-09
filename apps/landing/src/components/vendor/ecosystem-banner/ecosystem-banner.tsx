'use client';

import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react';

import { DEFAULT_ECOSYSTEM_PLATFORMS, type EcosystemPlatform } from './platforms';

/**
 * Schema-versioned dismissal record. Bump `BANNER_VERSION` when the platform
 * list or ticker behaviour materially changes.
 */
import { STORAGE_KEY, BANNER_VERSION, DISMISS_DAYS, MARQUEE_SECONDS_PER_PLATFORM, BANNER_STYLES } from './presentation';

interface DismissalRecord {
  v: number;
  dismissed_at: number;
}

function readDismissal(): DismissalRecord | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<DismissalRecord>;
    if (typeof parsed.dismissed_at !== 'number' || typeof parsed.v !== 'number') return null;
    return parsed as DismissalRecord;
  } catch {
    return null;
  }
}

function isStillDismissed(record: DismissalRecord | null): boolean {
  if (!record) return false;
  if (record.v !== BANNER_VERSION) return false;
  const ageMs = Date.now() - record.dismissed_at;
  return ageMs < DISMISS_DAYS * 24 * 60 * 60 * 1000;
}

export interface EcosystemBannerProps {
  /** Override the platform list (e.g. show only a subset on a niche landing). */
  platforms?: readonly EcosystemPlatform[];
  /** Seconds for one full marquee loop across the duplicated track. */
  marqueeDurationSec?: number;
  /** Optional className for the outer fixed wrapper. */
  className?: string;
  /** Override host display label (defaults to "MADFAM ECOSYSTEM"). */
  label?: string;
  /** Optional test id for host-app E2E selectors. */
  testId?: string;
  /** Force-render even if dismissed — useful for previews/Storybook. */
  forceVisible?: boolean;
}

/**
 * MADFAM Ecosystem Banner — sticky bottom NYSE-style marquee ticker.
 *
 * - Continuous horizontal scroll of every `[KEYWORD]: [PLATFORM]` pair.
 * - Dismissible for 30 days (versioned localStorage).
 * - Brand-neutral chrome for embedding on any landing.
 */
export function EcosystemBanner({
  platforms = DEFAULT_ECOSYSTEM_PLATFORMS,
  marqueeDurationSec,
  className,
  label = 'MADFAM ECOSYSTEM',
  testId,
  forceVisible = false,
}: EcosystemBannerProps) {
  const list = useMemo(() => platforms.filter((p) => p.keyword && p.name && p.url), [platforms]);
  const track = useMemo(() => [...list, ...list], [list]);
  const durationSec =
    marqueeDurationSec ?? Math.max(30, list.length * MARQUEE_SECONDS_PER_PLATFORM);

  const [mounted, setMounted] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (forceVisible) {
      setVisible(true);
      return;
    }
    if (list.length === 0) return;
    const dismissed = isStillDismissed(readDismissal());
    setVisible(!dismissed);
  }, [forceVisible, list.length]);

  const handleDismiss = useCallback(() => {
    setVisible(false);
    try {
      const record: DismissalRecord = { v: BANNER_VERSION, dismissed_at: Date.now() };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
    } catch {
      // localStorage unavailable — hide for this session only.
    }
  }, []);

  if (!mounted || !visible || list.length === 0) return null;

  const tickerSummary = list.map((p) => p.name).join(', ');

  return (
    <div
      role="complementary"
      aria-label={`MADFAM ecosystem ticker: ${tickerSummary}`}
      data-testid={testId}
      className={['madfam-eco-banner', className ?? ''].join(' ')}
      style={
        {
          '--madfam-marquee-duration': `${durationSec}s`,
        } as CSSProperties
      }
    >
      <style>{BANNER_STYLES}</style>
      <div className="madfam-eco-banner__inner">
        <span aria-hidden="true" className="madfam-eco-banner__label">
          {label}
        </span>

        <span aria-hidden="true" className="madfam-eco-banner__separator">
          /
        </span>

        <div className="madfam-eco-banner__viewport">
          <div className="madfam-eco-banner__track">
            {track.map((platform, index) => {
              const fullPair = `${platform.keyword}: ${platform.name}`;
              const isDuplicate = index >= list.length;
              return (
                <a
                  key={`${platform.name}-${index}`}
                  href={platform.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={fullPair}
                  className="madfam-eco-banner__item"
                  aria-hidden={isDuplicate ? true : undefined}
                  tabIndex={isDuplicate ? -1 : undefined}
                >
                  <span className="madfam-eco-banner__keyword">{platform.keyword}:</span>
                  <span className="madfam-eco-banner__name">{platform.name}</span>
                  <span className="madfam-eco-banner__external">↗</span>
                </a>
              );
            })}
          </div>
        </div>

        <button
          type="button"
          onClick={handleDismiss}
          aria-label="Dismiss MADFAM ecosystem ticker"
          className="madfam-eco-banner__dismiss"
        >
          <span aria-hidden="true" className="madfam-eco-banner__dismiss-glyph">
            ×
          </span>
        </button>
      </div>
    </div>
  );
}
