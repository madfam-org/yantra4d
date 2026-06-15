'use client';

import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react';

import { DEFAULT_ECOSYSTEM_PLATFORMS, type EcosystemPlatform } from './platforms';

/**
 * Schema-versioned dismissal record. Bump `BANNER_VERSION` when the platform
 * list or ticker behaviour materially changes.
 */
const STORAGE_KEY = 'madfam_ecosystem_banner';
const BANNER_VERSION = 4;
const DISMISS_DAYS = 30;
const MARQUEE_SECONDS_PER_PLATFORM = 6;

const BANNER_STYLES = `
  @keyframes ecosystemBannerIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes ecosystemMarquee {
    from { transform: translateX(0); }
    to { transform: translateX(-50%); }
  }

  .madfam-eco-banner {
    position: fixed;
    inset-inline: 0;
    bottom: 0;
    z-index: 40;
    background: rgb(15 23 42 / 95%);
    color: rgb(241 245 249);
    border-top: 1px solid rgb(30 41 59);
    backdrop-filter: blur(4px);
    animation: ecosystemBannerIn 300ms ease-out both;
    padding-bottom: env(safe-area-inset-bottom, 0);
    box-sizing: border-box;
  }

  .madfam-eco-banner *,
  .madfam-eco-banner *::before,
  .madfam-eco-banner *::after {
    box-sizing: border-box;
  }

  .madfam-eco-banner__inner {
    width: 100%;
    max-width: 1536px;
    height: 28px;
    margin-inline: auto;
    padding-inline: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    line-height: 1;
  }

  .madfam-eco-banner__label {
    display: none;
    flex-shrink: 0;
    border-radius: 2px;
    background: rgb(30 41 59);
    padding: 2px 6px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .025em;
    color: rgb(148 163 184);
    white-space: nowrap;
  }

  .madfam-eco-banner__separator {
    display: none;
    color: rgb(71 85 105);
  }

  .madfam-eco-banner__viewport {
    min-width: 0;
    flex: 1 1 auto;
    overflow: hidden;
    mask-image: linear-gradient(90deg, transparent, #000 3%, #000 97%, transparent);
  }

  .madfam-eco-banner__track {
    display: flex;
    align-items: center;
    width: max-content;
    gap: 28px;
    animation: ecosystemMarquee var(--madfam-marquee-duration, 78s) linear infinite;
    will-change: transform;
  }

  .madfam-eco-banner__item {
    display: inline-flex;
    flex-shrink: 0;
    align-items: baseline;
    gap: 6px;
    color: rgb(241 245 249);
    text-decoration: none;
    transition: color 150ms ease;
    vertical-align: baseline;
  }

  .madfam-eco-banner__item:hover {
    color: rgb(255 255 255);
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .madfam-eco-banner__item:focus-visible,
  .madfam-eco-banner__dismiss:focus-visible {
    outline: 2px solid rgb(148 163 184);
    outline-offset: 2px;
    border-radius: 2px;
  }

  .madfam-eco-banner__keyword {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    text-transform: uppercase;
    letter-spacing: .025em;
    color: rgb(148 163 184);
    white-space: nowrap;
  }

  .madfam-eco-banner__name {
    flex-shrink: 0;
    font-weight: 600;
    white-space: nowrap;
  }

  .madfam-eco-banner__external {
    margin-left: 2px;
    color: rgb(100 116 139);
  }

  .madfam-eco-banner__dismiss {
    position: relative;
    margin-right: -4px;
    width: 44px;
    height: 44px;
    flex: 0 0 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 0;
    padding: 0;
    background: transparent;
    color: rgb(148 163 184);
    cursor: pointer;
    transition: color 150ms ease;
    font: inherit;
  }

  .madfam-eco-banner__dismiss:hover {
    color: rgb(241 245 249);
  }

  .madfam-eco-banner__dismiss-glyph {
    font-size: 16px;
    line-height: 1;
  }

  @media (min-width: 640px) {
    .madfam-eco-banner__inner {
      font-size: 12px;
    }

    .madfam-eco-banner__label,
    .madfam-eco-banner__separator {
      display: inline-block;
    }

    .madfam-eco-banner__dismiss {
      width: 28px;
      height: 28px;
      flex-basis: 28px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .madfam-eco-banner,
    .madfam-eco-banner__dismiss {
      animation: none;
      transition: none;
    }

    .madfam-eco-banner__track {
      animation: none;
      flex-wrap: wrap;
      width: 100%;
      gap: 8px 16px;
    }
  }
`;

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
