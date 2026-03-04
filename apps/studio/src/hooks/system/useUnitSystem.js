import { useState, useCallback, useMemo } from 'react'

const MM_PER_INCH = 25.4
const MM3_PER_IN3 = MM_PER_INCH ** 3 // 16387.064

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

  /** Convert mm³ value to current unit (in³ or mm³) */
  const convertVolume = useCallback((mm3Value) => {
    if (unit === 'in') return mm3Value / MM3_PER_IN3
    return mm3Value
  }, [unit])

  /** Format mm³ value with unit³ suffix */
  const formatVolume = useCallback((mm3Value, precision = 0) => {
    const val = convertVolume(mm3Value)
    return `${val.toFixed(precision)} ${unit === 'in' ? 'in³' : 'mm³'}`
  }, [convertVolume, unit])

  /** Unit label for display */
  const label = unit === 'in' ? 'in' : 'mm'

  return useMemo(() => ({
    unit,
    setUnit: setUnitPersist,
    convert,
    format,
    convertVolume,
    formatVolume,
    label,
    toggle,
  }), [unit, setUnitPersist, convert, format, convertVolume, formatVolume, label, toggle])
}
