import { useState } from 'react'
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Tooltip } from "@/components/ui/tooltip"
import { Star } from 'lucide-react'

const MAX_TICK_MARK_STEPS = 30

export default function SliderControl({ param, value, onSliderChange, getLabel, language, t, unitSystem }) {
    const [editing, setEditing] = useState(false)
    const [editValue, setEditValue] = useState('')
    const decimals = param.step % 1 === 0 ? 0 : (param.step.toString().split('.')[1]?.length || 0)
    const safeValue = value ?? param.default

    // Detect dimensional params by checking if the English label contains "(mm)"
    const rawLabel = getLabel(param, 'label', 'en') || ''
    const isDimensional = rawLabel.includes('(mm)')
    const isInches = isDimensional && unitSystem?.unit === 'in'

    // Convert display value for dimensional params when in inches mode
    const rawDisplay = typeof safeValue === 'number' ? parseFloat(safeValue.toFixed(decimals)) : safeValue
    const displayValue = isInches && typeof rawDisplay === 'number'
        ? parseFloat(unitSystem.convert(rawDisplay).toFixed(decimals + 1))
        : rawDisplay

    // Replace (mm) with (in) in the displayed label when in inches mode
    const paramLabel = isInches
        ? getLabel(param, 'label', language).replace('(mm)', '(in)')
        : getLabel(param, 'label', language)

    const commitEdit = () => {
        let num = parseFloat(editValue)
        if (!isNaN(num)) {
            // If user entered inches, convert back to mm for backend
            if (isInches) {
                num = num * 25.4
            }
            const clamped = Math.min(param.max, Math.max(param.min, num))
            const stepped = Math.round(clamped / param.step) * param.step
            onSliderChange(param.id, [parseFloat(stepped.toFixed(4))])
        }
        setEditing(false)
    }

    const labelId = `param-label-${param.id}`

    const isDisabled = !!param.disabled

    return (
        <div className={`space-y-1 ${isDisabled ? 'opacity-50 pointer-events-none' : ''}`}>
            <div className="flex justify-between items-center gap-2">
                <Tooltip content={getLabel(param, 'tooltip', language)}>
                    <Label id={labelId} className="flex items-center gap-1 cursor-help flex-1 text-sm truncate" title={paramLabel}>
                        {paramLabel}
                    </Label>
                </Tooltip>
                <div className="flex-shrink-0 text-right w-16">
                    {editing ? (
                        <input
                            type="number"
                            inputMode="decimal"
                            className="w-full text-sm text-right bg-input border border-border rounded px-1 py-1 h-7"
                            value={editValue}
                            min={param.min} max={param.max} step={param.step}
                            autoFocus
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={commitEdit}
                            onKeyDown={(e) => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditing(false) }}
                        />
                    ) : (
                        <span
                            className="text-sm text-muted-foreground cursor-pointer hover:text-foreground transition-colors border-b border-dashed border-muted-foreground/60 hover:border-foreground focus-visible:ring-1 focus-visible:ring-ring focus-visible:rounded-sm h-7 inline-flex items-center justify-end w-full"
                            onClick={() => { setEditing(true); setEditValue(String(displayValue)) }}
                            role="button"
                            tabIndex={0}
                            aria-label={`${paramLabel}: ${displayValue}. ${t('ctrl.click_to_edit')}`}
                            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setEditing(true); setEditValue(String(displayValue)) } }}
                        >
                            {displayValue}
                        </span>
                    )}
                </div>
            </div>
            <Slider
                value={[safeValue]}
                min={param.min} max={param.max} step={param.step}
                onValueChange={(vals) => onSliderChange(param.id, vals, false)}
                onValueCommit={(vals) => onSliderChange(param.id, vals, true)}
                aria-labelledby={labelId}
            />
            {/* Tick marks with default star */}
            <div className="relative w-full h-4 -mt-1" aria-hidden="true">
                {(() => {
                    const stepCount = Math.round((param.max - param.min) / param.step) + 1
                    const showTicks = stepCount <= MAX_TICK_MARK_STEPS
                    const starValue = param.star ?? param.default
                    const starPct = ((starValue - param.min) / (param.max - param.min)) * 100

                    return (
                        <>
                            {showTicks && Array.from({ length: stepCount }, (_, i) => {
                                const val = param.min + i * param.step
                                const pct = ((val - param.min) / (param.max - param.min)) * 100
                                const isDefaultTick = Math.abs(val - param.default) < param.step / 2
                                if (isDefaultTick) return null
                                return (
                                    <div
                                        key={i}
                                        className="absolute top-0 w-px h-2 bg-muted-foreground/50"
                                        style={{ left: `${pct}%` }}
                                    />
                                )
                            })}
                            <div
                                className="absolute top-0 -translate-x-1/2"
                                style={{ left: `${starPct}%` }}
                                data-testid={`default-star-${param.id}`}
                            >
                                <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                            </div>
                        </>
                    )
                })()}
            </div>
            {param.description && (
                <p className="text-xs text-muted-foreground">{getLabel(param, 'description', language)}</p>
            )}
        </div>
    )
}
