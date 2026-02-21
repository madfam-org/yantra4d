import { useState, useEffect } from 'react'

/**
 * Parse hash segments into parts array, stripping leading #/ prefix.
 * @param {string} hash - window.location.hash value
 * @returns {string[]} parsed path segments
 */
function parseHashParts(hash) {
  return hash.replace(/^#\/?/, '').split('/').filter(Boolean)
}

/**
 * Check if the current hash represents the demo view.
 * @param {string} hash
 * @returns {boolean}
 */
export function isDemoView(hash) {
  const parts = parseHashParts(hash)
  return parts.length === 1 && parts[0] === 'demo'
}

/**
 * Check if the current hash represents the projects listing view.
 * @param {string} hash
 * @returns {boolean}
 */
export function isProjectsView(hash) {
  const parts = parseHashParts(hash)
  return parts.length === 1 && (parts[0] === 'projects' || parts[0] === 'demo')
}

/**
 * Parse the URL hash to extract the active preset and mode.
 * Supports both 2-segment (#preset/mode) and 3-segment (#project/preset/mode) formats.
 * @param {string} hash
 * @param {Array} presets - available presets from manifest
 * @param {Array} modes - available modes from manifest
 * @returns {{ preset: object|null, mode: object }}
 */
export function parseHash(hash, presets, modes) {
  const parts = parseHashParts(hash)
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
 * Build a canonical 3-segment hash string.
 * @param {string} projectSlug
 * @param {string} presetId
 * @param {string} modeId
 * @returns {string} hash string like #/project/preset/mode
 */
export function buildHash(projectSlug, presetId, modeId) {
  return `#/${projectSlug}/${presetId}/${modeId}`
}

/**
 * Hook that manages hash-based navigation state (current view, demo flag)
 * and listens for browser back/forward hash changes.
 *
 * @param {object} options
 * @param {Array} options.presets - available presets
 * @param {Array} options.modes - available modes from manifest
 * @param {string} options.projectSlug - current project slug
 * @param {function} options.onHashChange - callback when hash changes with parsed { mode, preset }
 * @returns {{ currentView: string, isDemo: boolean }}
 */
export function useHashNavigation({ presets, modes, projectSlug, onHashChange }) {
  const [isDemo, setIsDemo] = useState(() => isDemoView(window.location.hash))
  const [currentView, setCurrentView] = useState(() => {
    const hash = window.location.hash
    // Default to projects view if hash is empty or explicitly 'projects'
    if (!hash || hash === '#' || isProjectsView(hash)) return 'projects'
    return 'studio'
  })

  // Set initial hash if missing or invalid, BUT ONLY if we are in studio view.
  // If we are in projects view (root), we should not auto-select a project params hash.
  useEffect(() => {
    if (currentView === 'projects') return
    if (!modes || modes.length === 0) return
    const parsed = parseHash(window.location.hash, presets, modes)
    const presetId = parsed.preset?.id || presets[0]?.id
    const modeId = parsed.mode?.id || modes[0]?.id
    if (presetId && modeId) {
      // Use replaceState to avoid triggering hashchange — params are already
      // correctly initialized (including ?p= shared params) and a hashchange
      // would re-apply preset values, overriding shared params.
      history.replaceState(null, '', buildHash(projectSlug, presetId, modeId))
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for browser back/forward
  useEffect(() => {
    const handler = () => {
      if (isDemoView(window.location.hash)) {
        setIsDemo(true)
        setCurrentView('projects')
        return
      }
      if (isProjectsView(window.location.hash)) {
        setCurrentView('projects')
        return
      }
      setCurrentView('studio')
      if (!modes || modes.length === 0) return
      const parsed = parseHash(window.location.hash, presets, modes)
      onHashChange?.(parsed)
    }
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [presets, modes, onHashChange])

  return { currentView, isDemo }
}
