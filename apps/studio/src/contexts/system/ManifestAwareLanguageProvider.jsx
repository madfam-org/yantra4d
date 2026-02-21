import { useManifest } from "../project/ManifestProvider"
import { LanguageProvider } from "./LanguageProvider"

export default function ManifestAwareLanguageProvider({ children }) {
  const { projectSlug } = useManifest()
  return (
    <LanguageProvider defaultLanguage="es" storageKey={`${projectSlug}-lang`}>
      {children}
    </LanguageProvider>
  )
}
