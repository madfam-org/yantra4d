import AxisScaleHint from './AxisScaleHint'

/**
 * R3F overlay component that renders visual hints for the currently
 * hovered parameter. Orchestrates sub-visualizations based on hint type.
 *
 * Rendered inside the Canvas alongside the model.
 */
export default function ParameterPreviewOverlay({ hoveredParam, sceneBox, centerOfMass }) {
  if (!hoveredParam || !sceneBox) return null
  const { hint } = hoveredParam

  switch (hint.type) {
    case 'axis_scale':
      return <AxisScaleHint param={hoveredParam} bbox={sceneBox} centerOfMass={centerOfMass} />
    case 'part_highlight':
    case 'toggle_highlight':
      // Part highlighting is handled via highlightMode in Viewer's Model component
      return null
    default:
      return null
  }
}
