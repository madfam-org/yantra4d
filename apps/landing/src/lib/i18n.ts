import en from '../locales/en.json';
import es from '../locales/es.json';

const locales = { en, es } as const;

export type Locale = keyof typeof locales;
export type Translations = typeof en;

export function getTranslations(lang: Locale): Translations {
  return locales[lang] ?? locales.es;
}

export function getLangFromUrl(url: URL): Locale {
  const [, lang] = url.pathname.split('/');
  if (lang === 'en') return 'en';
  return 'es';
}
