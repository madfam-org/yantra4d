import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

/**
 * Parse path segments into parts array, stripping leading /project/ or /demo
 * @param {string} pathname - location.pathname value
 * @returns {string[]} parsed path segments
 */
function parsePathParts(pathname) {
  const parts = pathname.split('/').filter(Boolean)
  if (parts[0] === 'project' || parts[0] === 'projects') return parts.slice(1)
  if (parts[0] === 'demo') return parts
  return parts
}

/**
 * Check if the current path represents the demo view.
 * @param {string} pathname
 * @returns {boolean}
 */
export function isDemoView(pathname) {
  const parts = pathname.split('/').filter(Boolean)
  return parts.length > 0 && parts[0] === 'demo'
}

/**
 * Check if the current path represents the projects listing view.
 * @param {string} pathname
 * @returns {boolean}
 */
export function isProjectsView(pathname) {
  const parts = pathname.split('/').filter(Boolean)
  return parts.length === 0 || parts[0] === 'projects' || parts[0] === 'demo'
}

/**
 * Parse the URL path to extract the active mode and preset.
 * URL format: /project/{slug}/{modeId}/{presetId}
 * @param {string} pathname
 * @param {Array} presets - available presets from manifest
 * @param {Array} modes - available modes from manifest
 * @param {string} defaultModeId - Optional fallback mode ID
 * @param {string} defaultPresetId - Optional fallback preset ID
 * @returns {{ preset: object|null, mode: object }}
 */
export function parseHash(pathname, presets, modes, defaultModeId = null, defaultPresetId = null) {
  const parts = parsePathParts(pathname)
  let modeId, presetId

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

  let mode = modes.find(m => m.id === modeId)
  let preset = presets.find(p => p.id === presetId)

  // Use defined fallbacks if not explicitly found in the URL parts
  if (!preset && defaultPresetId) {
    preset = presets.find(p => p.id === defaultPresetId)
  }
  if (!mode && defaultModeId) {
    mode = modes.find(m => m.id === defaultModeId)
  }

  // If no explicit mode matched but we found a valid preset, default to its first allowed mode
  if (!mode && preset && preset.visible_in_modes && preset.visible_in_modes.length > 0) {
    mode = modes.find(m => m.id === preset.visible_in_modes[0])
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
 * @param {string} projectSlug
 * @param {string} modeId
 * @param {string} [presetId] - omitted if null/undefined
 * @returns {string} url string like /project/slug/mode/preset
 */
export function buildHash(projectSlug, modeId, presetId) {
  if (presetId) {
    return `/project/${projectSlug}/${modeId}/${presetId}`
  }
  return `/project/${projectSlug}/${modeId}`
}

/**
 * Hook that manages route-based navigation state (current view, demo flag)
 * and listens for browser navigation changes.
 *
 * @param {object} options
 * @param {Array} options.presets - available presets
 * @param {Array} options.modes - available modes from manifest
 * @param {string} options.projectSlug - current project slug
 * @param {function} options.onHashChange - callback when route changes with parsed { mode, preset }
 * @param {string} options.defaultModeId - Fallback mode id to use if path lacks one
 * @param {string} options.defaultPresetId - Fallback preset id to use if path lacks one
 * @returns {{ currentView: string, isDemo: boolean }}
 */
export function useHashNavigation({ presets, modes, projectSlug, onHashChange, defaultModeId, defaultPresetId }) {
  const location = useLocation()
  const navigate = useNavigate()

  const [isDemo, setIsDemo] = useState(() => isDemoView(location.pathname))
  const [currentView, setCurrentView] = useState(() => {
    if (isProjectsView(location.pathname)) return 'projects'
    return 'studio'
  })

  // Set initial path if missing or invalid, BUT ONLY if we are in studio view.
  useEffect(() => {
    if (currentView === 'projects') return
    if (!modes || modes.length === 0) return
    const parsed = parseHash(location.pathname, presets, modes, defaultModeId, defaultPresetId)
    const presetId = parsed.preset?.id || presets[0]?.id
    const modeId = parsed.mode?.id || modes[0]?.id

    // Only replace if the path doesn't already have these set
    const expectedPath = buildHash(projectSlug, modeId, presetId)
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
