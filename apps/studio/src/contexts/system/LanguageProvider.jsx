import { createContext, useContext, useState, useEffect, useMemo, useCallback } from "react"
import esLocale from '../../locales/es'
import enLocale from '../../locales/en'
import ptLocale from '../../locales/pt'
import frLocale from '../../locales/fr'
import deLocale from '../../locales/de'
import zhLocale from '../../locales/zh'

const LanguageProviderContext = createContext()

// All locales keyed by language code; en is the ultimate fallback
const locales = { es: esLocale, en: enLocale, pt: ptLocale, fr: frLocale, de: deLocale, zh: zhLocale }

function resolveTranslation(lang, key) {
    return locales[lang]?.[key] || locales.en?.[key] || key
}

export function LanguageProvider({
    children,
    defaultLanguage = "es",
    storageKey = "yantra4d-lang",
}) {
    const [language, setLanguage] = useState(() => {
        try { return localStorage.getItem(storageKey) || defaultLanguage } catch { return defaultLanguage }
    })

    const t = useCallback((key) => {
        return resolveTranslation(language, key)
    }, [language])

    // Sync <html lang> attribute with current language (WCAG 3.1.1)
    useEffect(() => {
        document.documentElement.lang = language
    }, [language])

    const setLang = useCallback((lang) => {
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

// eslint-disable-next-line react-refresh/only-export-components
export const useLanguage = () => {
    const context = useContext(LanguageProviderContext)

    if (context === undefined)
        throw new Error("useLanguage must be used within a LanguageProvider")

    return context
}
