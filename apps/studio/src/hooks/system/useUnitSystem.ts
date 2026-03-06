import { useState, useCallback, useMemo } from 'react'

const MM_PER_INCH = 25.4
const MM3_PER_IN3 = MM_PER_INCH ** 3 // 16387.064

type UnitType = 'mm' | 'in'

interface UnitSystem {
  unit: UnitType
  setUnit: (newUnit: UnitType) => void
  convert: (mmValue: number) => number
  format: (mmValue: number, precision?: number) => string
  convertVolume: (mm3Value: number) => number
  formatVolume: (mm3Value: number, precision?: number) => string
  label: string
  toggle: () => void
}

/**
 * Hook for display-only unit conversion (mm <-> inches).
 * All internal values remain in mm. This only affects formatted output.
 */
export function useUnitSystem(): UnitSystem {
  const [unit, setUnit] = useState<UnitType>(() => {
    try {
      return (localStorage.getItem('yantra4d-unit') as UnitType) || 'mm'
    } catch {
      return 'mm'
    }
  })

  const setUnitPersist = useCallback((newUnit: UnitType) => {
    setUnit(newUnit)
    try {
      localStorage.setItem('yantra4d-unit', newUnit)
    } catch { /* ignore */ }
  }, [])

  const toggle = useCallback(() => {
    setUnitPersist(unit === 'mm' ? 'in' : 'mm')
  }, [unit, setUnitPersist])

  /** Convert mm value to current unit */
  const convert = useCallback((mmValue: number): number => {
    if (unit === 'in') return mmValue / MM_PER_INCH
    return mmValue
  }, [unit])

  /** Format mm value with unit suffix */
  const format = useCallback((mmValue: number, precision: number = 1): string => {
    const val = convert(mmValue)
    return `${val.toFixed(precision)}${unit === 'in' ? '"' : 'mm'}`
  }, [convert, unit])

  /** Convert mm3 value to current unit (in3 or mm3) */
  const convertVolume = useCallback((mm3Value: number): number => {
    if (unit === 'in') return mm3Value / MM3_PER_IN3
    return mm3Value
  }, [unit])

  /** Format mm3 value with unit3 suffix */
  const formatVolume = useCallback((mm3Value: number, precision: number = 0): string => {
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
