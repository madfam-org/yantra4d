import { createContext, useContext, useState, useEffect, useMemo, useCallback } from "react"
import esLocale from '../../locales/es.json'
import enLocale from '../../locales/en.json'
import ptLocale from '../../locales/pt.json'
import frLocale from '../../locales/fr.json'
import deLocale from '../../locales/de.json'
import zhLocale from '../../locales/zh.json'

export interface LanguageContextValue {
    language: string
    setLanguage: (lang: string) => void
    t: (key: string, params?: Record<string, string | number>) => string
}

interface LanguageProviderProps {
    children: React.ReactNode
    defaultLanguage?: string
    storageKey?: string
}

const LanguageProviderContext = createContext<LanguageContextValue | undefined>(undefined)

// All locales keyed by language code; en is the ultimate fallback
const locales: Record<string, Record<string, string>> = { es: esLocale, en: enLocale, pt: ptLocale, fr: frLocale, de: deLocale, zh: zhLocale }

function resolveTranslation(lang: string, key: string): string {
    return locales[lang]?.[key] || locales.en?.[key] || key
}

/** Language codes the Studio ships a locale file for. */
export const SUPPORTED_LANGUAGES: readonly string[] = Object.keys(locales)

/**
 * The first of the browser's preferred languages the Studio has a locale for,
 * matched on the primary subtag (`en-US` -> `en`, `pt-BR` -> `pt`), or null.
 *
 * `navigator.languages` is the visitor's ordered list; `navigator.language`
 * is the fallback for browsers that only expose one. Never throws: a missing
 * or odd `navigator` (SSR, a locked-down embed) is simply "no preference".
 */
export function browserPreferredLanguage(
    nav: { languages?: readonly string[]; language?: string } | null =
        typeof navigator === 'undefined' ? null : navigator,
): string | null {
    if (!nav) return null
    const candidates = [...(nav.languages ?? []), nav.language ?? '']
    for (const tag of candidates) {
        const primary = String(tag || '').trim().toLowerCase().split(/[-_]/)[0]
        if (primary && SUPPORTED_LANGUAGES.includes(primary)) return primary
    }
    return null
}

export function LanguageProvider({
    children,
    defaultLanguage = "es",
    storageKey = "yantra4d-lang",
}: LanguageProviderProps) {
    const [language, setLanguage] = useState(() => {
        try { return localStorage.getItem(storageKey) || defaultLanguage } catch { return defaultLanguage }
    })

    const t = useCallback((key: string, params?: Record<string, string | number>) => {
        let str = resolveTranslation(language, key)
        if (params) {
            for (const [k, v] of Object.entries(params)) {
                str = str.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
            }
        }
        return str
    }, [language])

    // Sync <html lang> attribute with current language (WCAG 3.1.1)
    useEffect(() => {
        document.documentElement.lang = language
    }, [language])

    const setLang = useCallback((lang: string) => {
        try { localStorage.setItem(storageKey, lang) } catch { /* quota exceeded or private browsing */ }
        setLanguage(lang)
    }, [storageKey])

    const value = useMemo(() => ({
        language,
        setLanguage: setLang,
        t,
    }), [language, setLang, t])

    return (
        <LanguageProviderContext.Provider value={value}>
            {children}
        </LanguageProviderContext.Provider>
    )
}

export const useLanguage = (): LanguageContextValue => {
    const context = useContext(LanguageProviderContext)

    if (context === undefined)
        throw new Error("useLanguage must be used within a LanguageProvider")

    return context
}
