import { Button } from '@/components/ui/button'
import { Plus, Trash2, ChevronUp, ChevronDown } from 'lucide-react'

function getStepLabel(step, language) {
  if (!step.label) return `Step ${step.step}`
  if (typeof step.label === 'string') return step.label
  return step.label[language] || step.label.en || `Step ${step.step}`
}

export default function StepList({ steps, selectedIndex, onSelect, onAdd, onRemove, onReorder, language }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-muted-foreground font-medium">Steps ({steps.length})</span>
        <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={onAdd}>
          <Plus className="h-3 w-3 mr-1" /> Add
        </Button>
      </div>

      <div className="flex flex-col gap-0.5 max-h-48 overflow-y-auto">
        {steps.map((step, i) => (
          <div
            key={i}
            role="button"
            tabIndex={0}
            className={`flex items-center gap-1 px-2 py-1.5 rounded text-xs cursor-pointer transition-colors ${
              i === selectedIndex
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-muted'
            }`}
            onClick={() => onSelect(i)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(i) } }}
          >
            <span className="font-medium w-5 shrink-0">{step.step}.</span>
            <span className="flex-1 truncate">{getStepLabel(step, language) || '(untitled)'}</span>

            {i === selectedIndex && (
              <div className="flex items-center gap-0.5">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={(e) => { e.stopPropagation(); onReorder(i, -1) }}
                  disabled={i === 0}
                >
                  <ChevronUp className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0"
                  onClick={(e) => { e.stopPropagation(); onReorder(i, 1) }}
                  disabled={i === steps.length - 1}
                >
                  <ChevronDown className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 w-5 p-0 text-destructive"
                  onClick={(e) => { e.stopPropagation(); onRemove(i) }}
                  disabled={steps.length <= 1}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
