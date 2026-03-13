import { useState, useCallback, useEffect, useRef } from 'react'

const STORAGE_KEY = 'yantra4d-panel-layout'
const DEBOUNCE_MS = 300

const DEFAULT_LAYOUT = {
  sidebarSize: 25,
  sidebarCollapsed: false,
  consoleSize: 30,
  consoleCollapsed: false,
}

function readStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_LAYOUT
    const parsed = JSON.parse(raw)
    return { ...DEFAULT_LAYOUT, ...parsed }
  } catch {
    return DEFAULT_LAYOUT
  }
}

function writeStorage(layout) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout))
  } catch {
    // quota exceeded or unavailable — silently ignore
  }
}

export function usePanelLayout() {
  const [layout, setLayout] = useState(readStorage)
  const timerRef = useRef(null)

  // Debounced persistence
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => writeStorage(layout), DEBOUNCE_MS)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [layout])

  const setSidebarSize = useCallback((size) => {
    setLayout(prev => ({ ...prev, sidebarSize: size }))
  }, [])

  const toggleSidebar = useCallback(() => {
    setLayout(prev => ({ ...prev, sidebarCollapsed: !prev.sidebarCollapsed }))
  }, [])

  const setConsoleSize = useCallback((size) => {
    setLayout(prev => ({ ...prev, consoleSize: size }))
  }, [])

  const toggleConsole = useCallback(() => {
    setLayout(prev => ({ ...prev, consoleCollapsed: !prev.consoleCollapsed }))
  }, [])

  return {
    layout,
    setSidebarSize,
    toggleSidebar,
    setConsoleSize,
    toggleConsole,
  }
}
