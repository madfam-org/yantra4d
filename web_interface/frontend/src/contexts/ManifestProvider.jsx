import { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react"
import fallbackManifest from "../config/fallback-manifest.json"
import { getApiBase } from "../services/backendDetection"

const ManifestContext = createContext()

export function ManifestProvider({ children }) {
  const [manifest, setManifest] = useState(fallbackManifest)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Try backend API first; fall back to bundled manifest (always available for static deploy)
    fetch(`${getApiBase()}/api/manifest`, { signal: AbortSignal.timeout(2000) })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => setManifest(data))
      .catch((err) => {
        console.warn('Manifest fetch failed, using fallback:', err)
      })
      .finally(() => setLoading(false))
  }, [])

  const getMode = useCallback((modeId) => manifest.modes.find((m) => m.id === modeId), [manifest])

  const getParametersForMode = useCallback((modeId) =>
    manifest.parameters.filter(
      (p) => !p.visible_in_modes || p.visible_in_modes.includes(modeId)
    ), [manifest])

  const getPartColors = useCallback((modeId) => {
    const mode = getMode(modeId)
    if (!mode) return []
    return mode.parts.map((pid) => manifest.parts.find((p) => p.id === pid)).filter(Boolean)
  }, [manifest, getMode])

  const getDefaultParams = useCallback(() => {
    const result = {}
    for (const p of manifest.parameters) {
      result[p.id] = p.default
    }
    return result
  }, [manifest])

  const getDefaultColors = useCallback(() => {
    const result = {}
    for (const p of manifest.parts) {
      result[p.id] = p.default_color
    }
    return result
  }, [manifest])

  const getLabel = useCallback((obj, key, lang) => {
    if (!obj || !obj[key]) return ""
    if (typeof obj[key] === "string") return obj[key]
    return obj[key][lang] || obj[key]["en"] || ""
  }, [])

  const getCameraViews = useCallback(() => manifest.camera_views || [], [manifest])

  const getGroupLabel = useCallback((groupId, lang) => {
    const group = (manifest.parameter_groups || []).find((g) => g.id === groupId)
    if (!group) return groupId
    return getLabel(group, "label", lang)
  }, [manifest, getLabel])

  const getViewerConfig = useCallback(() => manifest.viewer || {}, [manifest])

  const getEstimateConstants = useCallback(() => manifest.estimate_constants || {}, [manifest])

  const value = useMemo(() => ({
    manifest,
    loading,
    getMode,
    getParametersForMode,
    getPartColors,
    getDefaultParams,
    getDefaultColors,
    getLabel,
    getCameraViews,
    getGroupLabel,
    getViewerConfig,
    getEstimateConstants,
    presets: manifest.presets || [],
    projectSlug: manifest.project.slug,
  }), [manifest, loading, getMode, getParametersForMode, getPartColors, getDefaultParams, getDefaultColors, getLabel, getCameraViews, getGroupLabel, getViewerConfig, getEstimateConstants])

  return <ManifestContext.Provider value={value}>{children}</ManifestContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useManifest = () => {
  const context = useContext(ManifestContext)
  if (context === undefined) throw new Error("useManifest must be used within a ManifestProvider")
  return context
}
