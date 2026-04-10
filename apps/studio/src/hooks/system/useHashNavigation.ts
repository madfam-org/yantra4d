import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

interface ModeConfig {
  id: string
  [key: string]: unknown
}

interface Preset {
  id: string
  values: Record<string, unknown>
  visible_in_modes?: string[]
  [key: string]: unknown
}

interface ParsedHash {
  preset: Preset | null
  mode: ModeConfig | null
}

interface HashNavigationOptions {
  presets: Preset[]
  modes: ModeConfig[]
  projectSlug: string
  onHashChange?: (parsed: ParsedHash) => void
  defaultModeId?: string | null
  defaultPresetId?: string | null
}

interface HashNavigationResult {
  currentView: 'projects' | 'studio' | 'onboard'
  isDemo: boolean
}

/**
 * Parse path segments into parts array, stripping leading /project/ or /demo
 */
function parsePathParts(pathname: string): string[] {
  const parts = pathname.split('/').filter(Boolean)
  if (parts[0] === 'project' || parts[0] === 'projects') return parts.slice(1)
  if (parts[0] === 'demo') return parts
  return parts
}

/**
 * Check if the current path represents the demo view.
 */
export function isDemoView(pathname: string): boolean {
  const parts = pathname.split('/').filter(Boolean)
  return parts.length > 0 && parts[0] === 'demo'
}

/**
 * Check if the current path represents the projects listing view.
 */
export function isProjectsView(pathname: string): boolean {
  const parts = pathname.split('/').filter(Boolean)
  return parts.length === 0 || parts[0] === 'projects' || parts[0] === 'demo'
}

/**
 * Check if the current path represents the onboarding wizard view.
 */
export function isOnboardView(pathname: string): boolean {
  const parts = pathname.split('/').filter(Boolean)
  return parts.length > 0 && parts[0] === 'onboard'
}

/**
 * Parse the URL path to extract the active mode and preset.
 * URL format: /project/{slug}/{modeId}/{presetId}
 */
export function parseHash(
  pathname: string,
  presets: Preset[],
  modes: ModeConfig[],
  defaultModeId: string | null = null,
  defaultPresetId: string | null = null
): ParsedHash {
  const parts = parsePathParts(pathname)
  let modeId: string | null
  let presetId: string | null

  if (parts.length >= 3) {
    modeId = parts[1]
    presetId = parts[2]
  } else if (parts.length === 2) {
    modeId = parts[1]
    presetId = null
  } else {
    modeId = null
    presetId = null
  }

  let mode = modes.find(m => m.id === modeId) || null
  let preset = presets.find(p => p.id === presetId) || null

  // Use defined fallbacks if not explicitly found in the URL parts
  if (!preset && defaultPresetId) {
    preset = presets.find(p => p.id === defaultPresetId) || null
  }
  if (!mode && defaultModeId) {
    mode = modes.find(m => m.id === defaultModeId) || null
  }

  // If no explicit mode matched but we found a valid preset, default to its first allowed mode
  if (!mode && preset && preset.visible_in_modes && preset.visible_in_modes.length > 0) {
    mode = modes.find(m => m.id === preset!.visible_in_modes![0]) || null
  }

  // Final fallback
  if (!mode) {
    mode = modes.length > 0 ? modes[0] : null
  }

  return {
    preset: preset || presets[0] || null,
    mode: mode,
  }
}

/**
 * Build a canonical path string: /project/{slug}/{modeId}/{presetId}
 */
export function buildHash(projectSlug: string, modeId: string, presetId?: string | null): string {
  if (presetId) {
    return `/project/${projectSlug}/${modeId}/${presetId}`
  }
  return `/project/${projectSlug}/${modeId}`
}

/**
 * Hook that manages route-based navigation state (current view, demo flag)
 * and listens for browser navigation changes.
 */
export function useHashNavigation({
  presets,
  modes,
  projectSlug,
  onHashChange,
  defaultModeId,
  defaultPresetId
}: HashNavigationOptions): HashNavigationResult {
  const location = useLocation()
  const navigate = useNavigate()

  const [isDemo, setIsDemo] = useState(() => isDemoView(location.pathname))
  const [currentView, setCurrentView] = useState<'projects' | 'studio' | 'onboard'>(() => {
    if (isOnboardView(location.pathname)) return 'onboard'
    if (isProjectsView(location.pathname)) return 'projects'
    return 'studio'
  })

  // Set initial path if missing or invalid, BUT ONLY if we are in studio view.
  useEffect(() => {
    if (currentView !== 'studio') return
    if (!modes || modes.length === 0) return
    const parsed = parseHash(location.pathname, presets, modes, defaultModeId, defaultPresetId)
    const presetId = parsed.preset?.id || presets[0]?.id
    const modeId = parsed.mode?.id || modes[0]?.id

    // Only replace if the path doesn't already have these set
    const expectedPath = buildHash(projectSlug, modeId!, presetId)
    if (presetId && modeId && location.pathname !== expectedPath && !location.pathname.includes(expectedPath)) {
      navigate(expectedPath + location.search, { replace: true })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for navigation changes
  useEffect(() => {
    if (isDemoView(location.pathname)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsDemo(true)

      setCurrentView('projects')
      return
    }
    if (isOnboardView(location.pathname)) {
      setCurrentView('onboard')
      return
    }
    if (isProjectsView(location.pathname)) {
      setCurrentView('projects')
      return
    }
    setCurrentView('studio')
    if (!modes || modes.length === 0) return
    const parsed = parseHash(location.pathname, presets, modes, defaultModeId, defaultPresetId)
    onHashChange?.(parsed)
  }, [location.pathname, presets, modes, onHashChange, defaultModeId, defaultPresetId])

  return { currentView, isDemo }
}
