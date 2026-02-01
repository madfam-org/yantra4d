import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

export default function PartVisibilityPicker({ allParts, visibleParts, highlightParts, onChange }) {
  const toggleVisible = (partId) => {
    const newVisible = visibleParts.includes(partId)
      ? visibleParts.filter(p => p !== partId)
      : [...visibleParts, partId]
    // If removing from visible, also remove from highlight
    const newHighlight = newVisible.includes(partId)
      ? highlightParts
      : highlightParts.filter(p => p !== partId)
    onChange(newVisible, newHighlight)
  }

  const toggleHighlight = (partId) => {
    // Can only highlight if visible
    if (!visibleParts.includes(partId)) return
    const newHighlight = highlightParts.includes(partId)
      ? highlightParts.filter(p => p !== partId)
      : [...highlightParts, partId]
    onChange(visibleParts, newHighlight)
  }

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-3">
      <span className="text-xs font-medium text-muted-foreground">Part Visibility</span>
      <div className="grid grid-cols-[1fr_auto_auto] gap-x-3 gap-y-1 items-center">
        <span className="text-[10px] text-muted-foreground">Part</span>
        <span className="text-[10px] text-muted-foreground text-center">Visible</span>
        <span className="text-[10px] text-muted-foreground text-center">Highlight</span>

        {allParts.map(partId => (
          <div key={partId} className="contents">
            <Label className="text-xs truncate">{partId}</Label>
            <div className="flex justify-center">
              <Checkbox
                checked={visibleParts.includes(partId)}
                onCheckedChange={() => toggleVisible(partId)}
              />
            </div>
            <div className="flex justify-center">
              <Checkbox
                checked={highlightParts.includes(partId)}
                onCheckedChange={() => toggleHighlight(partId)}
                disabled={!visibleParts.includes(partId)}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
