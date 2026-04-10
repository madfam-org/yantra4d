import { LanguageProvider } from "./LanguageProvider"

interface ManifestAwareLanguageProviderProps {
  children: React.ReactNode
}

export default function ManifestAwareLanguageProvider({ children }: ManifestAwareLanguageProviderProps) {
  return (
    <LanguageProvider defaultLanguage="es" storageKey="yantra4d-lang">
      {children}
    </LanguageProvider>
  )
}
