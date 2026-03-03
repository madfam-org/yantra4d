import { useState, useCallback, useMemo } from 'react'

const MM_PER_INCH = 25.4

/**
 * Hook for display-only unit conversion (mm ↔ inches).
 * All internal values remain in mm. This only affects formatted output.
 *
 * @returns {{ unit, setUnit, convert, format, label, toggle }}
 */
export function useUnitSystem() {
  const [unit, setUnit] = useState(() => {
    try {
      return localStorage.getItem('yantra4d-unit') || 'mm'
    } catch {
      return 'mm'
    }
  })

  const setUnitPersist = useCallback((newUnit) => {
    setUnit(newUnit)
    try {
      localStorage.setItem('yantra4d-unit', newUnit)
    } catch { /* ignore */ }
  }, [])

  const toggle = useCallback(() => {
    setUnitPersist(unit === 'mm' ? 'in' : 'mm')
  }, [unit, setUnitPersist])

  /** Convert mm value to current unit */
  const convert = useCallback((mmValue) => {
    if (unit === 'in') return mmValue / MM_PER_INCH
    return mmValue
  }, [unit])

  /** Format mm value with unit suffix */
  const format = useCallback((mmValue, precision = 1) => {
    const val = convert(mmValue)
    return `${val.toFixed(precision)}${unit === 'in' ? '"' : 'mm'}`
  }, [convert, unit])

  /** Unit label for display */
  const label = unit === 'in' ? 'in' : 'mm'

  return useMemo(() => ({
    unit,
    setUnit: setUnitPersist,
    convert,
    format,
    label,
    toggle,
  }), [unit, setUnitPersist, convert, format, label, toggle])
}
