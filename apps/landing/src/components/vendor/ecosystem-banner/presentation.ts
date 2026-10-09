/** Shared presentation contract for React and static Astro hosts. */
export const STORAGE_KEY = 'madfam_ecosystem_banner';
export const BANNER_VERSION = 4;
export const DISMISS_DAYS = 30;
export const MARQUEE_SECONDS_PER_PLATFORM = 6;

export const BANNER_STYLES = `
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
      flex-wrap: nowrap;
      width: max-content;
    }

    .madfam-eco-banner__viewport {
      overflow-x: auto;
      scrollbar-width: thin;
      scrollbar-color: rgb(71 85 105) transparent;
      mask-image: none;
    }

    .madfam-eco-banner__item[aria-hidden="true"] {
      display: none;
    }
  }
`;

