/**
 * Infers a preview hint for a parameter based on its definition,
 * the manifest, and the current mode. Used by the hover-to-preview
 * system to show directional arrows and part highlights.
 *
 * @param {object} paramDef - Parameter definition from the manifest
 * @param {object} manifest - Full project manifest
 * @param {string} mode - Current mode ID
 * @returns {{ type: string, axis?: string, affected_parts?: string[], scale_factor?: number }}
 */
export function inferPreviewHint(paramDef, manifest, mode) {
  // 1. Use explicit preview_hint from manifest if present
  if (paramDef.preview_hint) return paramDef.preview_hint

  const label = (paramDef.label?.en || '').toLowerCase()
  const currentMode = manifest?.modes?.find(m => m.id === mode)
  const affectedParts = currentMode?.parts || []

  // 2. Dimensional sliders — infer axis from label
  if (paramDef.type === 'slider') {
    if (label.includes('width') || /\bx\b/.test(label))
      return { type: 'axis_scale', axis: 'x', affected_parts: affectedParts }
    if (label.includes('depth') || label.includes('length') || /\by\b/.test(label))
      return { type: 'axis_scale', axis: 'y', affected_parts: affectedParts }
    if (label.includes('height') || /\bz\b/.test(label))
      return { type: 'axis_scale', axis: 'z', affected_parts: affectedParts }
    if (label.includes('diameter') || label.includes('radius'))
      return { type: 'axis_scale', axis: 'radial', affected_parts: affectedParts }
    // Non-dimensional slider — part highlight only
    return { type: 'part_highlight', affected_parts: affectedParts }
  }

  // 3. Checkboxes — toggle geometry
  if (paramDef.type === 'checkbox')
    return { type: 'toggle_highlight', affected_parts: affectedParts }

  // 4. Selects — part highlight
  if (paramDef.type === 'select')
    return { type: 'part_highlight', affected_parts: affectedParts }

  return { type: 'none' }
}
