import { createContext, useContext, useEffect, useState, useMemo, useCallback } from "react"

type Theme = 'light' | 'dark' | 'system'

interface ThemeContextValue {
    theme: string
    setTheme: (theme: string) => void
}

interface ThemeProviderProps {
    children: React.ReactNode
    defaultTheme?: string
    storageKey?: string
}

const ThemeProviderContext = createContext<ThemeContextValue | undefined>(undefined)

export function ThemeProvider({
    children,
    defaultTheme = "system",
    storageKey = "yantra4d-theme",
}: ThemeProviderProps) {
    const [theme, setTheme] = useState(() => {
        try { return localStorage.getItem(storageKey) || defaultTheme } catch { return defaultTheme }
    })

    useEffect(() => {
        const root = window.document.documentElement

        root.classList.remove("light", "dark")

        if (theme === "system") {
            const systemTheme = window.matchMedia("(prefers-color-scheme: dark)")
                .matches
                ? "dark"
                : "light"

            root.classList.add(systemTheme)
            return
        }

        root.classList.add(theme)
    }, [theme])

    const handleSetTheme = useCallback((newTheme: string) => {
        try { localStorage.setItem(storageKey, newTheme) } catch { /* quota exceeded or private browsing */ }
        setTheme(newTheme)
    }, [storageKey])

    const value = useMemo(() => ({
        theme,
        setTheme: handleSetTheme,
    }), [theme, handleSetTheme])

    return (
        <ThemeProviderContext.Provider value={value}>
            {children}
        </ThemeProviderContext.Provider>
    )
}

export const useTheme = (): ThemeContextValue => {
    const context = useContext(ThemeProviderContext)

    if (context === undefined)
        throw new Error("useTheme must be used within a ThemeProvider")

    return context
}
