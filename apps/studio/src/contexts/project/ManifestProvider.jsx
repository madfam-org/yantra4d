import { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react"
import { useLocation } from "react-router-dom"
import fallbackManifest from "../../config/fallback-manifest"
import { getApiBase } from "../../services/core/backendDetection"

const ManifestContext = createContext()

const PROJECTS_FETCH_TIMEOUT_MS = 2000

export function ManifestProvider({ children }) {
  const location = useLocation()
  const [manifest, setManifest] = useState(fallbackManifest)
  const [projects, setProjects] = useState([])
  const [projectSlug, setProjectSlug] = useState(() => _getProjectSlug(location))
  const [loading, setLoading] = useState(true)
  // Track whether the projects list has been fetched (or failed).
  // The manifest fetch must wait for this so it can use the correct endpoint.
  const [projectsResolved, setProjectsResolved] = useState(false)

  // Fetch projects list on mount
  useEffect(() => {
    fetch(`${getApiBase()}/api/projects`, { signal: AbortSignal.timeout(PROJECTS_FETCH_TIMEOUT_MS) })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        setProjects(data)
        // Determine initial project from URL location
        const foundSlug = _getProjectSlug(location)
        const slug = data.find(p => p.slug === foundSlug)?.slug
        if (slug) {
          setProjectSlug(slug)
        } else {
          // If no project in hash, ensure we don't have a stale fallback
          setProjectSlug(null)
          setLoading(false)
        }
        setProjectsResolved(true)
      })
      .catch((err) => {
        console.warn('Projects fetch failed, using fallback:', err)
        setProjectSlug(fallbackManifest.project.slug)
        setProjectsResolved(true)
        setLoading(false)
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Fetch manifest when projectSlug changes — only after projects list resolves
  useEffect(() => {
    if (!projectSlug || !projectsResolved) return

    const controller = new AbortController()
    setLoading(true)  
    const url = projects.length > 0
      ? `${getApiBase()}/api/projects/${projectSlug}/manifest`
      : `${getApiBase()}/api/manifest`

    fetch(url, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => setManifest(data))
      .catch((err) => {
        if (err.name === 'AbortError') return
        console.warn('Manifest fetch failed, using fallback:', err)
        setManifest(fallbackManifest)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    return () => controller.abort()
  }, [projectSlug, projects.length, projectsResolved])

  // Listen for location changes to detect cross-project navigation
  useEffect(() => {
    const newSlug = _getProjectSlug(location)
    if (newSlug && newSlug !== projectSlug) {
       
      setProjectSlug(newSlug)
    }
  }, [location, projectSlug])

  // ready = manifest has loaded and matches the requested project
  const ready = !loading && manifest.project?.slug === projectSlug

  const switchProject = useCallback((slug) => {
    setProjectSlug(slug)
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
    ready,
    projects,
    projectSlug: projectSlug || manifest.project.slug,
    switchProject,
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
  }), [manifest, loading, ready, projects, projectSlug, switchProject, getMode, getParametersForMode, getPartColors, getDefaultParams, getDefaultColors, getLabel, getCameraViews, getGroupLabel, getViewerConfig, getEstimateConstants])

  return <ManifestContext.Provider value={value}>{children}</ManifestContext.Provider>
}

function _getProjectSlug(location) {
  if (!location) return null;
  // Support both hash-based #/slug and path-based /project/slug
  const hash = location.hash.replace(/^#\/?/, '')
  const hashParts = hash.split('/').filter(Boolean)
  if (hashParts.length >= 1) return hashParts[0]

  const pathParts = location.pathname.split('/').filter(Boolean)
  if (pathParts[0] === 'project' && pathParts.length >= 2) {
    return pathParts[1]
  }

  return null
}

// eslint-disable-next-line react-refresh/only-export-components
export const useManifest = () => {
  const context = useContext(ManifestContext)
  if (context === undefined) throw new Error("useManifest must be used within a ManifestProvider")
  return context
}
