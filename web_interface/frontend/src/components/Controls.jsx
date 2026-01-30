import React, { useState } from 'react'
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Checkbox } from "@/components/ui/checkbox"
import { useLanguage } from "../contexts/LanguageProvider"
import { useManifest } from "../contexts/ManifestProvider"
import { Tooltip } from "@/components/ui/tooltip"
import { Star } from 'lucide-react'

function SliderControl({ param, value, onSliderChange, getLabel, language }) {
    const [editing, setEditing] = useState(false)
    const [editValue, setEditValue] = useState('')

    const commitEdit = () => {
        const num = parseFloat(editValue)
        if (!isNaN(num)) {
            const clamped = Math.min(param.max, Math.max(param.min, num))
            const stepped = Math.round(clamped / param.step) * param.step
            onSliderChange(param.id, [parseFloat(stepped.toFixed(4))])
        }
        setEditing(false)
    }

    const labelId = `param-label-${param.id}`

    return (
        <div className="space-y-2">
            <div className="flex justify-between items-center">
                <Tooltip content={getLabel(param, 'tooltip', language)}>
                    <Label id={labelId} className="flex items-center gap-2 cursor-help">
                        {getLabel(param, 'label', language)}

                    </Label>
                </Tooltip>
                {editing ? (
                    <input
                        type="number"
                        className="w-16 text-sm text-right bg-input border border-border rounded px-1 py-0.5"
                        value={editValue}
                        min={param.min} max={param.max} step={param.step}
                        autoFocus
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={commitEdit}
                        onKeyDown={(e) => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditing(false) }}
                    />
                ) : (
                    <span
                        className="text-sm text-muted-foreground cursor-pointer hover:text-foreground transition-colors"
                        onClick={() => { setEditing(true); setEditValue(String(value)) }}
                        role="button"
                        tabIndex={0}
                        aria-label={`${getLabel(param, 'label', language)}: ${value}. Click to edit`}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setEditing(true); setEditValue(String(value)) } }}
                    >
                        {value}
                    </span>
                )}
            </div>
            <Slider
                value={[value]}
                min={param.min} max={param.max} step={param.step}
                onValueChange={(vals) => onSliderChange(param.id, vals)}
                aria-labelledby={labelId}
            />
            {/* Tick marks with default star */}
            <div className="relative w-full h-4 -mt-1" aria-hidden="true">
                {(() => {
                    const stepCount = Math.round((param.max - param.min) / param.step) + 1
                    const showTicks = stepCount <= 30
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
                                        className="absolute top-0 w-px h-2 bg-muted-foreground/30"
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

export default function Controls({ params, setParams, mode, colors, setColors }) {
    const { language } = useLanguage()
    const { getParametersForMode, getPartColors, getLabel, getGroupLabel } = useManifest()
    const [visibilityLevel, setVisibilityLevel] = useState('basic')

    const handleSliderChange = (name, valArray) => {
        setParams(prev => ({ ...prev, [name]: valArray[0] }))
    }

    const handleCheckedChange = (name, checked) => {
        setParams(prev => ({ ...prev, [name]: checked }))
    }

    const handleColorChange = (key, val) => {
        setColors(prev => ({ ...prev, [key]: val }))
    }

    const parametersForMode = getParametersForMode(mode)
    const sliders = parametersForMode.filter(p => p.type === 'slider')
    const checkboxes = parametersForMode.filter(p => p.type === 'checkbox')
    const visibilityCheckboxes = checkboxes.filter(p => p.group === 'visibility')
    const otherCheckboxes = checkboxes.filter(p => !p.group)

    // Filter visibility checkboxes by level
    const filteredVisibility = visibilityCheckboxes.filter(p => {
        if (visibilityLevel === 'basic') {
            return !p.visibility_level || p.visibility_level === 'basic'
        }
        return true // advanced shows all
    })

    const partColors = getPartColors(mode)

    const isParentUnchecked = (param) => {
        if (!param.parent) return false
        return params[param.parent] === false
    }

    return (
        <div className="flex flex-col gap-6">
            {/* Sliders */}
            {sliders.length > 0 && (
                <div className="space-y-4">
                    {sliders.map(param => (
                        <SliderControl
                            key={param.id}
                            param={param}
                            value={params[param.id]}
                            onSliderChange={handleSliderChange}
                            getLabel={getLabel}
                            language={language}
                        />
                    ))}
                </div>
            )}

            {/* Visibility checkboxes */}
            {visibilityCheckboxes.length > 0 && (
                <div className="space-y-4 border-t border-border pt-4">
                    <div className="flex justify-between items-center">
                        <Label className="text-base font-semibold">{getGroupLabel('visibility', language)}</Label>
                        <button
                            type="button"
                            className="text-xs text-muted-foreground hover:text-foreground transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                            onClick={() => setVisibilityLevel(prev => prev === 'basic' ? 'advanced' : 'basic')}
                        >
                            {visibilityLevel === 'basic'
                                ? (language === 'es' ? 'Avanzado' : 'Advanced')
                                : (language === 'es' ? 'Básico' : 'Basic')}
                        </button>
                    </div>
                    {filteredVisibility.map(param => {
                        const isChild = param.visibility_level === 'advanced' && param.parent
                        const disabled = isParentUnchecked(param)
                        return (
                            <div key={param.id} className={`flex items-center space-x-2 ${isChild ? 'ml-4' : ''}`}>
                                <Checkbox
                                    id={param.id}
                                    checked={!!params[param.id]}
                                    onCheckedChange={(c) => handleCheckedChange(param.id, c)}
                                    disabled={disabled}
                                />
                                <Tooltip content={getLabel(param, 'tooltip', language)}>
                                    <Label
                                        htmlFor={param.id}
                                        className={`cursor-help ${disabled ? 'opacity-50' : ''}`}
                                    >
                                        {getLabel(param, 'label', language)}
                                    </Label>
                                </Tooltip>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* Other checkboxes */}
            {otherCheckboxes.map(param => (
                <div key={param.id} className="flex items-center space-x-2">
                    <Checkbox
                        id={param.id}
                        checked={!!params[param.id]}
                        onCheckedChange={(c) => handleCheckedChange(param.id, c)}
                    />
                    <Tooltip content={getLabel(param, 'tooltip', language)}>
                        <Label htmlFor={param.id} className="cursor-help">
                            {getLabel(param, 'label', language)}
                        </Label>
                    </Tooltip>
                </div>
            ))}

            {/* Color Controls */}
            {partColors.length > 0 && (
                <div className="space-y-4 border-t border-border pt-4">
                    <Label className="text-base font-semibold">{getGroupLabel('colors', language)}</Label>
                    <div className={`grid gap-2 ${partColors.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
                        {partColors.map((part) => (
                            <div key={part.id} className="flex flex-col gap-1">
                                <Label className="text-xs">{getLabel(part, 'label', language)}</Label>
                                <input
                                    type="color"
                                    className="w-full h-8 cursor-pointer"
                                    value={colors[part.id] || part.default_color}
                                    onChange={(e) => handleColorChange(part.id, e.target.value)}
                                />
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
