import en from '../locales/en.json';
import es from '../locales/es.json';

/**
 * Locales with copy on disk. RFC 0039 (phase G-P) makes the landing
 * quadrilingual: `fr` and `pt` are PLANNED — routes and fallbacks are in place
 * so adding a locale is one JSON file plus one entry here, and the key-parity
 * test (`i18n.test.ts`) guards every file that exists. No route is served for a
 * planned locale until its copy exists; shipping English under /fr would be
 * worse than shipping nothing.
 */
const locales = { en, es } as const;

export const SUPPORTED_LOCALES = ['es', 'en'] as const;
export const PLANNED_LOCALES = ['fr', 'pt'] as const;
export const DEFAULT_LOCALE = 'es' as const;

export type Locale = keyof typeof locales;
export type PlannedLocale = (typeof PLANNED_LOCALES)[number];
export type Translations = typeof en;

export function isSupportedLocale(value: string | null | undefined): value is Locale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(value ?? '');
}

export function getTranslations(lang: Locale): Translations {
  return locales[lang] ?? locales[DEFAULT_LOCALE];
}

/** The locale a path is served in. Unknown and planned prefixes fall back to Spanish. */
export function getLangFromUrl(url: URL): Locale {
  const [, lang] = url.pathname.split('/');
  return isSupportedLocale(lang) ? lang : DEFAULT_LOCALE;
}

/** The same path in another supported locale (Spanish is unprefixed). */
export function localizedPath(pathname: string, target: Locale): string {
  const stripped = pathname.replace(/^\/(en|fr|pt)(?=\/|$)/, '') || '/';
  if (target === DEFAULT_LOCALE) return stripped;
  return `/${target}${stripped === '/' ? '/' : stripped}`;
}

/** `"Showing {shown} of {total}"` → `"Showing 24 of 502"`; unknown keys stay visible. */
export { fillTemplate } from './gallery';
