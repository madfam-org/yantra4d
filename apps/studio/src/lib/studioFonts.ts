/**
 * Fonts for drei's `<Text>` (troika-three-text), served from this origin. Without an explicit
 * `font`, troika resolves fonts at runtime from cdn.jsdelivr.net and fonts.gstatic.com, which the
 * Studio's CSP (`connect-src 'self' …`) blocks: no glyphs, one "Failed to fetch" per label
 * (2026-10-18). Roboto Regular, Latin subset, Apache License 2.0.
 */
export const STUDIO_LABEL_FONT = '/fonts/roboto-regular.woff'
