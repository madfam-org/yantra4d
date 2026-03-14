import AxisScaleHint from './AxisScaleHint'
import GhostGeometryOverlay from './GhostGeometryOverlay'

/**
 * R3F overlay component that renders visual hints for the currently
 * hovered parameter. Orchestrates sub-visualizations based on hint type.
 *
 * When cachedVariants are available (from IDB pre-render cache), renders
 * semi-transparent ghost meshes showing the parameter's min/max geometry.
 *
 * Rendered inside the Canvas alongside the model.
 */
export default function ParameterPreviewOverlay({ hoveredParam, sceneBox, centerOfMass, cachedVariants }) {
  if (!hoveredParam || !sceneBox) return null
  const { hint } = hoveredParam
  const variants = cachedVariants?.get?.(hoveredParam.paramId)

  switch (hint.type) {
    case 'axis_scale':
      return (
        <>
          <AxisScaleHint param={hoveredParam} bbox={sceneBox} centerOfMass={centerOfMass} />
          {variants && <GhostGeometryOverlay variants={variants} />}
        </>
      )
    case 'part_highlight':
    case 'toggle_highlight':
      // Part highlighting is handled via highlightMode in Viewer's Model component
      // If cached geometry exists, show ghost overlay for these types too
      return variants ? <GhostGeometryOverlay variants={variants} /> : null
    default:
      return null
  }
}
