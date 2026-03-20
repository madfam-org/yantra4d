import { useState, useCallback, useEffect, useRef } from 'react'

const STORAGE_KEY = 'yantra4d-panel-layout'
const DEBOUNCE_MS = 300

interface PanelLayout {
  sidebarSize: number
  sidebarCollapsed: boolean
  consoleSize: number
  consoleCollapsed: boolean
}

interface PanelLayoutHook {
  layout: PanelLayout
  setSidebarSize: (size: number) => void
  toggleSidebar: () => void
  setConsoleSize: (size: number) => void
  toggleConsole: () => void
}

const DEFAULT_LAYOUT: PanelLayout = {
  sidebarSize: 25,
  sidebarCollapsed: false,
  consoleSize: 30,
  consoleCollapsed: false,
}

function readStorage(): PanelLayout {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_LAYOUT
    const parsed = JSON.parse(raw)
    const merged: PanelLayout = { ...DEFAULT_LAYOUT, ...parsed }
    // Clamp corrupted sizes from the broken layout period
    if (merged.sidebarSize < 15 || merged.sidebarSize > 40) merged.sidebarSize = DEFAULT_LAYOUT.sidebarSize
    if (merged.consoleSize < 10 || merged.consoleSize > 50) merged.consoleSize = DEFAULT_LAYOUT.consoleSize
    return merged
  } catch {
    return DEFAULT_LAYOUT
  }
}

function writeStorage(layout: PanelLayout): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout))
  } catch {
    // quota exceeded or unavailable — silently ignore
  }
}

export function usePanelLayout(): PanelLayoutHook {
  const [layout, setLayout] = useState<PanelLayout>(readStorage)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Debounced persistence
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => writeStorage(layout), DEBOUNCE_MS)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [layout])

  const setSidebarSize = useCallback((size: number) => {
    setLayout(prev => ({ ...prev, sidebarSize: size }))
  }, [])

  const toggleSidebar = useCallback(() => {
    setLayout(prev => ({ ...prev, sidebarCollapsed: !prev.sidebarCollapsed }))
  }, [])

  const setConsoleSize = useCallback((size: number) => {
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
