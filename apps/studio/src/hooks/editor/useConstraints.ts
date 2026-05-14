import { useMemo } from 'react'
import { evaluateSafeFormula } from '../../lib/safeFormula'

interface Constraint {
  rule: string
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
      try {
        const result = evaluateSafeFormula(constraint.rule, params)
        if (!result) {
          const violation: Violation = {
            rule: constraint.rule,
            message: constraint.message,
            severity: constraint.severity,
            appliesTo: constraint.applies_to || [],
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
