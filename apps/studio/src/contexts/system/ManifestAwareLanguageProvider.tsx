import { useState } from "react"
import { LanguageProvider, browserPreferredLanguage } from "./LanguageProvider"

/** Spanish when the browser names no language the Studio ships. */
const FALLBACK_LANGUAGE = "es"

interface ManifestAwareLanguageProviderProps {
  children: React.ReactNode
}

/**
 * The Studio's language: the visitor's stored choice (the language toggle
 * writes `yantra4d-lang`), else the browser's preferred language when the
 * Studio has a locale for it, else Spanish. The browser guess is only the
 * DEFAULT, never stored, so an `en-US` visitor gets English without that being
 * pinned, and the toggle still has the last word.
 */
export default function ManifestAwareLanguageProvider({ children }: ManifestAwareLanguageProviderProps) {
  const [defaultLanguage] = useState(() => browserPreferredLanguage() ?? FALLBACK_LANGUAGE)
  return (
    <LanguageProvider defaultLanguage={defaultLanguage} storageKey="yantra4d-lang">
      {children}
    </LanguageProvider>
  )
}
