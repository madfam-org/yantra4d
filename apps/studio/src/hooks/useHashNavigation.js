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
 * Parse the URL path to extract the active preset and mode.
 * Supports both 2-segment (/project/.../preset/mode) formats.
 * @param {string} pathname
 * @param {Array} presets - available presets from manifest
 * @param {Array} modes - available modes from manifest
 * @returns {{ preset: object|null, mode: object }}
 */
export function parseHash(pathname, presets, modes) {
  const parts = parsePathParts(pathname)
  let presetId, modeId

  if (parts.length >= 3) {
    presetId = parts[1]
    modeId = parts[2]
  } else if (parts.length === 2) {
    presetId = parts[1]
    modeId = null
  } else {
    presetId = null
    modeId = null
  }

  const preset = presets.find(p => p.id === presetId)
  let mode = modes.find(m => m.id === modeId)

  // If no explict mode matched but we found a valid preset, default to its first allowed mode
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
 * Build a canonical 3-segment path string.
 * @param {string} projectSlug
 * @param {string} presetId
 * @param {string} modeId
 * @returns {string} url string like /project/slug/preset/mode
 */
export function buildHash(projectSlug, presetId, modeId) {
  return `/project/${projectSlug}/${presetId}/${modeId}`
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
 * @returns {{ currentView: string, isDemo: boolean }}
 */
export function useHashNavigation({ presets, modes, projectSlug, onHashChange }) {
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
    const parsed = parseHash(location.pathname, presets, modes)
    const presetId = parsed.preset?.id || presets[0]?.id
    const modeId = parsed.mode?.id || modes[0]?.id

    // Only replace if the path doesn't already have these set
    const expectedPath = buildHash(projectSlug, presetId, modeId)
    if (presetId && modeId && location.pathname !== expectedPath && !location.pathname.includes(expectedPath)) {
      navigate(expectedPath, { replace: true })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for navigation changes
  useEffect(() => {
    if (isDemoView(location.pathname)) {
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
    const parsed = parseHash(location.pathname, presets, modes)
    onHashChange?.(parsed)
  }, [location.pathname, presets, modes, onHashChange])

  return { currentView, isDemo }
}
