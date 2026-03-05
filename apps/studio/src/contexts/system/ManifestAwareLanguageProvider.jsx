import { LanguageProvider } from "./LanguageProvider"

export default function ManifestAwareLanguageProvider({ children }) {
  return (
    <LanguageProvider defaultLanguage="es" storageKey="yantra4d-lang">
      {children}
    </LanguageProvider>
  )
}
