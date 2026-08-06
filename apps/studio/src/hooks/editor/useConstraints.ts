import { useMemo } from 'react'
import { evaluateSafeFormula } from '../../lib/safeFormula'

interface Constraint {
  // Authored manifests declare the formula as `expression` (e.g. "grid_x * grid_y <= 24");
  // a legacy shape used `rule`. Accept either so the 555 authored constraints across the
  // commons actually evaluate (they use `expression`).
  expression?: string
  rule?: string
  message: string | Record<string, string>
  severity: string
  applies_to?: string[]
}

interface Violation {
  rule: string
  message: string | Record<string, string>
  severity: string
  appliesTo: string[]
}

interface ConstraintResult {
  violations: Violation[]
  byParam: Record<string, Violation[]>
  hasErrors: boolean
}

/**
 * Evaluate manifest constraints against current parameter values.
 * Returns violations grouped by parameter ID and overall validity.
 */
export function useConstraints(
  constraints: Constraint[] | undefined | null,
  params: Record<string, unknown>
): ConstraintResult {
  return useMemo(() => {
    if (!constraints || constraints.length === 0) {
      return { violations: [], byParam: {}, hasErrors: false }
    }

    const violations: Violation[] = []
    const byParam: Record<string, Violation[]> = {}

    for (const constraint of constraints) {
      const formula = constraint.expression ?? constraint.rule
      if (!formula) continue
      try {
        const result = evaluateSafeFormula(formula, params)
        if (!result) {
          // When applies_to isn't declared, attach the violation to every parameter the
          // formula references, so the offending controls light up.
          const appliesTo = constraint.applies_to?.length
            ? constraint.applies_to
            : Object.keys(params).filter(id => new RegExp(`\\b${id}\\b`).test(formula))
          const violation: Violation = {
            rule: formula,
            message: constraint.message,
            severity: constraint.severity,
            appliesTo,
          }
          violations.push(violation)
          for (const paramId of violation.appliesTo) {
            if (!byParam[paramId]) byParam[paramId] = []
            byParam[paramId].push(violation)
          }
        }
      } catch {
        // Skip constraints that fail to evaluate (missing params, etc.)
      }
    }

    return {
      violations,
      byParam,
      hasErrors: violations.some(v => v.severity === 'error'),
    }
  }, [constraints, params])
}
