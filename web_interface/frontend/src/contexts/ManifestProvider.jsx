import { createContext, useContext, useState, useEffect } from "react"
import fallbackManifest from "../config/fallback-manifest.json"

const ManifestContext = createContext()

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000"

export function ManifestProvider({ children }) {
  const [manifest, setManifest] = useState(fallbackManifest)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/api/manifest`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => setManifest(data))
      .catch((err) => {
        console.warn("Manifest fetch failed, using bundled fallback:", err.message)
      })
      .finally(() => setLoading(false))
  }, [])

  const getMode = (modeId) => manifest.modes.find((m) => m.id === modeId)

  const getParametersForMode = (modeId) =>
    manifest.parameters.filter(
      (p) => !p.visible_in_modes || p.visible_in_modes.includes(modeId)
    )

  const getPartColors = (modeId) => {
    const mode = getMode(modeId)
    if (!mode) return []
    return mode.parts.map((pid) => manifest.parts.find((p) => p.id === pid)).filter(Boolean)
  }

  const getDefaultParams = () => {
    const result = {}
    for (const p of manifest.parameters) {
      result[p.id] = p.default
    }
    return result
  }

  const getDefaultColors = () => {
    const result = {}
    for (const p of manifest.parts) {
      result[p.id] = p.default_color
    }
    return result
  }

  const getLabel = (obj, key, lang) => {
    if (!obj || !obj[key]) return ""
    if (typeof obj[key] === "string") return obj[key]
    return obj[key][lang] || obj[key]["en"] || ""
  }

  const value = {
    manifest,
    loading,
    getMode,
    getParametersForMode,
    getPartColors,
    getDefaultParams,
    getDefaultColors,
    getLabel,
    projectSlug: manifest.project.slug,
  }

  return <ManifestContext.Provider value={value}>{children}</ManifestContext.Provider>
}

export const useManifest = () => {
  const context = useContext(ManifestContext)
  if (context === undefined) throw new Error("useManifest must be used within a ManifestProvider")
  return context
}
