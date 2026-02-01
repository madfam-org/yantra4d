import { useMemo } from 'react'
import { Parser } from 'expr-eval'

const parser = new Parser()

/**
 * Evaluate manifest constraints against current parameter values.
 * Returns violations grouped by parameter ID and overall validity.
 */
export function useConstraints(constraints, params) {
  return useMemo(() => {
    if (!constraints || constraints.length === 0) {
      return { violations: [], byParam: {}, hasErrors: false }
    }

    const violations = []
    const byParam = {}

    for (const constraint of constraints) {
      try {
        const expr = parser.parse(constraint.rule)
        const result = expr.evaluate(params)
        if (!result) {
          const violation = {
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
