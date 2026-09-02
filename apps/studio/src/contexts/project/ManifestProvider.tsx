import { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react"
import { useLocation } from "react-router-dom"
import type { Location } from "react-router-dom"
import fallbackManifest from "../../config/fallback-manifest.json"
import { getApiBase } from "../../services/core/backendDetection"
import { apiFetch } from "../../services/core/apiClient"
import { useAuth } from "../auth/AuthProvider"

interface ManifestMode {
  id: string
  parts: string[]
  estimate?: {
    formula?: string
    formula_vars?: string[]
    base_units?: number
  }
  [key: string]: unknown
}

interface ManifestParameter {
  id: string
  type: string
  default: unknown
  group?: string
  visible_in_modes?: string[]
  label?: Record<string, string>
  min?: number
  max?: number
  preview_hint?: { type: string; axis?: string; affected_parts?: string[] }
  [key: string]: unknown
}

interface ManifestPart {
  id: string
  default_color: string
  render_mode: number
  [key: string]: unknown
}

interface CameraView {
  id: string
  [key: string]: unknown
}

interface ParameterGroup {
  id: string
  label: string | Record<string, string>
  [key: string]: string | Record<string, string> | undefined
}

interface Preset {
  id: string
  values: Record<string, unknown>
  mode?: string
  visible_in_modes?: string[]
  [key: string]: unknown
}

export interface Manifest {
  project: { slug: string; name?: string | Record<string, string>; force_backend?: boolean; hard_reload?: boolean; [key: string]: unknown }
  modes: ManifestMode[]
  parameters: ManifestParameter[]
  parts: ManifestPart[]
  camera_views?: CameraView[]
  parameter_groups?: ParameterGroup[]
  viewer?: Record<string, unknown>
  estimate_constants?: Record<string, unknown>
  // Constraints declare parameter interdependencies. Authored manifests use `expression`
  // (e.g. "grid_x * grid_y <= 24"); a legacy shape used `rule`. Both are optional so the
  // fallback manifest and the 555 authored constraints across the commons both type-check.
  constraints?: Array<{ expression?: string; rule?: string; message: string | Record<string, string>; severity: string; applies_to?: string[] }>
  grid_presets?: Record<string, unknown>
  presets?: Preset[]
  [key: string]: unknown
}

interface ProjectListItem {
  slug: string
  [key: string]: unknown
}

export interface Localizable {
  [key: string]: string | Record<string, string> | undefined
}

/**
 * Why the manifest could not be loaded.
 *
 * 'project_locked' is a private project: the backend answers 401/403 with
 * `error_code: "project_locked"`. That is neither a missing project nor an
 * unreachable server, and the user can often fix it by signing in — so it
 * needs its own kind rather than being folded into 'manifest_load_failed'.
 */
export type ManifestErrorKind =
  | 'project_not_found'
  | 'project_locked'
  | 'manifest_load_failed'
  | 'network_error'

/** Error body shape shared by the backend's 4xx JSON responses. */
interface ManifestErrorBody {
  error?: string
  error_code?: string
  auth_required?: boolean
}

export interface ManifestContextValue {
  manifest: Manifest
  loading: boolean
  ready: boolean
  manifestError: ManifestErrorKind | null
  /**
   * Only meaningful for 'project_locked': true when the caller was anonymous,
   * so signing in with an authorized account can unlock the project; false when
   * the caller is already signed in and simply is not authorized.
   */
  manifestAuthRequired: boolean
  projects: ProjectListItem[]
  projectSlug: string
  switchProject: (slug: string) => void
  getMode: (modeId: string) => ManifestMode | undefined
  getParametersForMode: (modeId: string) => ManifestParameter[]
  getPartColors: (modeId: string) => ManifestPart[]
  getDefaultParams: () => Record<string, unknown>
  getDefaultColors: () => Record<string, string>
  getLabel: (obj: Localizable | Record<string, unknown> | null | undefined, key: string, lang: string) => string
  getCameraViews: () => CameraView[]
  getGroupLabel: (groupId: string, lang: string) => string
  getViewerConfig: () => Record<string, unknown>
  getEstimateConstants: () => Record<string, unknown>
  presets: Preset[]
}

interface ManifestProviderProps {
  children: React.ReactNode
}

const ManifestContext = createContext<ManifestContextValue | undefined>(undefined)

const PROJECTS_FETCH_TIMEOUT_MS = 2000

export function ManifestProvider({ children }: ManifestProviderProps) {
  const location = useLocation()
  // Auth-disabled builds fall back to the bypass context, where this is false.
  const { isAuthenticated } = useAuth()
  const signedIn = Boolean(isAuthenticated)
  const [manifest, setManifest] = useState<Manifest>(fallbackManifest as Manifest)
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [projectSlug, setProjectSlug] = useState<string | null>(() => _getProjectSlug(location))
  const [loading, setLoading] = useState(true)
  const [manifestError, setManifestError] = useState<ManifestErrorKind | null>(null)
  const [manifestAuthRequired, setManifestAuthRequired] = useState(false)
  // Track whether the projects list has been fetched (or failed).
  // The manifest fetch must wait for this so it can use the correct endpoint.
  const [projectsResolved, setProjectsResolved] = useState(false)
  // ...and whether it actually SUCCEEDED. "Resolved" is true either way, so on
  // its own it cannot tell a single-project backend (list loaded, empty) from a
  // list fetch that failed or timed out. Those need opposite endpoints.
  const [projectsListLoaded, setProjectsListLoaded] = useState(false)

  // Fetch projects list on mount
  useEffect(() => {
    apiFetch(`${getApiBase()}/api/projects`, { signal: AbortSignal.timeout(PROJECTS_FETCH_TIMEOUT_MS) })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        setProjects(data)
        // Determine initial project from URL location
        const foundSlug = _getProjectSlug(location)
        const listedSlug = data.find((p: ProjectListItem) => p.slug === foundSlug)?.slug
        if (listedSlug) {
          setProjectSlug(listedSlug)
        } else if (foundSlug) {
          // Slug from URL not in public list (may be unlisted) — try it anyway
          setProjectSlug(foundSlug)
        } else {
          // No project in URL at all
          setProjectSlug(null)
          setLoading(false)
        }
        setProjectsResolved(true)
        setProjectsListLoaded(true)
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
    // Only a backend that answered with an EMPTY list is single-project, and
    // only that one serves the slug-less /api/manifest — anywhere PROJECTS_DIR
    // is set it answers 400 ("project query param required"), which lands in
    // the else-branch below as `manifest_load_failed` and replaces the whole app
    // with "Can't Reach the Server".
    //
    // This used to key off `projects.length > 0`, which cannot tell that case
    // from a list fetch that never delivered — and the list fetch aborts itself
    // after PROJECTS_FETCH_TIMEOUT_MS. On a 500-cartridge commons that abort is
    // routine under load: nightly run #170 logged `GET /api/projects 200` at
    // 05:02:23 and a slug-less `GET /api/manifest` 400 exactly 2 s later, with
    // no per-slug request at all, and the studio showed the error screen for a
    // project whose own manifest endpoint was answering fine.
    //
    // We have `projectSlug` here — the effect returns above without one — so the
    // per-slug endpoint is always the right question to ask unless the backend
    // has told us there are no projects to ask about.
    const singleProjectBackend = projectsListLoaded && projects.length === 0
    const url = singleProjectBackend
      ? `${getApiBase()}/api/manifest`
      : `${getApiBase()}/api/projects/${projectSlug}/manifest`

    apiFetch(url, { signal: controller.signal })
      .then(async (res) => {
        if (!res.ok) {
          // The body carries `error_code` and `auth_required` for a private
          // project. It is read defensively: an error response is not
          // guaranteed to be JSON (a proxy or CDN may answer with HTML).
          const body = (await res.json().catch(() => null)) as ManifestErrorBody | null
          if (res.status === 404) {
            setManifestAuthRequired(false)
            setManifestError('project_not_found')
          } else if (res.status === 401 || res.status === 403 || body?.error_code === 'project_locked') {
            // When the body omits the flag, fall back to what the client knows:
            // an anonymous caller can still fix this by signing in.
            setManifestAuthRequired(typeof body?.auth_required === 'boolean' ? body.auth_required : !signedIn)
            setManifestError('project_locked')
          } else {
            setManifestAuthRequired(false)
            setManifestError('manifest_load_failed')
          }
          setLoading(false)
          return undefined
        }
        return res.json()
      })
      .then((data) => {
        if (data) {
          setManifestError(null)
          setManifestAuthRequired(false)
          setManifest(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        console.warn('Manifest fetch failed:', err)
        setManifestAuthRequired(false)
        setManifestError('network_error')
        setLoading(false)
      })

    return () => controller.abort()
    // `signedIn` is a dependency so that a successful sign-in re-fetches the
    // manifest: a project that answered 403 while anonymous may now be allowed.
  }, [projectSlug, projects.length, projectsListLoaded, projectsResolved, signedIn])

  // Listen for location changes to detect cross-project navigation
  useEffect(() => {
    const newSlug = _getProjectSlug(location)
    if (newSlug && newSlug !== projectSlug) {

      setProjectSlug(newSlug)
    }
  }, [location, projectSlug])

  // ready = manifest has loaded and matches the requested project
  const ready = !loading && manifest.project?.slug === projectSlug

  const switchProject = useCallback((slug: string) => {
    setProjectSlug(slug)
  }, [])

  const getMode = useCallback((modeId: string) => manifest.modes.find((m) => m.id === modeId), [manifest])

  const getParametersForMode = useCallback((modeId: string) =>
    manifest.parameters.filter(
      (p) => !p.visible_in_modes || p.visible_in_modes.includes(modeId)
    ), [manifest])

  const getPartColors = useCallback((modeId: string) => {
    const mode = getMode(modeId)
    if (!mode) return []
    return mode.parts.map((pid) => manifest.parts.find((p) => p.id === pid)).filter((p): p is ManifestPart => Boolean(p))
  }, [manifest, getMode])

  const getDefaultParams = useCallback(() => {
    const result: Record<string, unknown> = {}
    for (const p of manifest.parameters) {
      result[p.id] = p.default
    }
    return result
  }, [manifest])

  const getDefaultColors = useCallback(() => {
    const result: Record<string, string> = {}
    for (const p of manifest.parts) {
      result[p.id] = p.default_color
    }
    return result
  }, [manifest])

  const getLabel = useCallback((obj: Localizable | Record<string, unknown> | null | undefined, key: string, lang: string) => {
    if (!obj || !obj[key]) return ""
    if (typeof obj[key] === "string") return obj[key] as string
    return (obj[key] as Record<string, string>)[lang] || (obj[key] as Record<string, string>)["en"] || ""
  }, [])

  const getCameraViews = useCallback(() => manifest.camera_views || [], [manifest])

  const getGroupLabel = useCallback((groupId: string, lang: string) => {
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
    manifestError,
    manifestAuthRequired,
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
  }), [manifest, loading, ready, manifestError, manifestAuthRequired, projects, projectSlug, switchProject, getMode, getParametersForMode, getPartColors, getDefaultParams, getDefaultColors, getLabel, getCameraViews, getGroupLabel, getViewerConfig, getEstimateConstants])

  return <ManifestContext.Provider value={value}>{children}</ManifestContext.Provider>
}

function _getProjectSlug(location: Location): string | null {
  if (!location) return null;
  // Primary: path-based /project/slug (BrowserRouter)
  const pathParts = location.pathname.split('/').filter(Boolean)
  if (pathParts[0] === 'project' && pathParts.length >= 2) {
    return pathParts[1]
  }

  // Legacy fallback: hash-based #/slug (auto-redirected by main.jsx pre-mount script)
  const hash = location.hash.replace(/^#\/?/, '')
  const hashParts = hash.split('/').filter(Boolean)
  if (hashParts.length >= 1) return hashParts[0]

  return null
}

export const useManifest = (): ManifestContextValue => {
  const context = useContext(ManifestContext)
  if (context === undefined) throw new Error("useManifest must be used within a ManifestProvider")
  return context
}
