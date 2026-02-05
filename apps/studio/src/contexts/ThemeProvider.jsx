import { createContext, useContext, useEffect, useState, useMemo, useCallback } from "react"

const ThemeProviderContext = createContext()

export function ThemeProvider({
    children,
    defaultTheme = "system",
    storageKey = "qubic-theme",
}) {
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

    const handleSetTheme = useCallback((newTheme) => {
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

// eslint-disable-next-line react-refresh/only-export-components
export const useTheme = () => {
    const context = useContext(ThemeProviderContext)

    if (context === undefined)
        throw new Error("useTheme must be used within a ThemeProvider")

    return context
}
