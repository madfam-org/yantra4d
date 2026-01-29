import React, { useState } from 'react'
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Checkbox } from "@/components/ui/checkbox"
import { useLanguage } from "../contexts/LanguageProvider"
import { useManifest } from "../contexts/ManifestProvider"
import { Tooltip } from "@/components/ui/tooltip"
import { Star } from 'lucide-react'

function SliderControl({ param, value, onSliderChange, getLabel, language, isDefault }) {
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

    return (
        <div className="space-y-2">
            <div className="flex justify-between items-center">
                <Tooltip content={getLabel(param, 'tooltip', language)}>
                    <Label className="flex items-center gap-2 cursor-help">
                        {getLabel(param, 'label', language)}
                        {isDefault && <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />}
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
                        title="Click to edit"
                    >
                        {value}
                    </span>
                )}
            </div>
            <Slider
                value={[value]}
                min={param.min} max={param.max} step={param.step}
                onValueChange={(vals) => onSliderChange(param.id, vals)}
            />
            {param.description && (
                <p className="text-xs text-muted-foreground">{getLabel(param, 'description', language)}</p>
            )}
        </div>
    )
}

export default function Controls({ params, setParams, mode, colors, setColors }) {
    const { language } = useLanguage()
    const { getParametersForMode, getPartColors, getLabel } = useManifest()

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

    const partColors = getPartColors(mode)

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
                            isDefault={params[param.id] === param.default}
                        />
                    ))}
                </div>
            )}

            {/* Visibility checkboxes */}
            {visibilityCheckboxes.length > 0 && (
                <div className="space-y-4 border-t border-border pt-4">
                    <Label className="text-base font-semibold">{language === 'es' ? 'Visibilidad' : 'Visibility'}</Label>
                    {visibilityCheckboxes.map(param => (
                        <div key={param.id} className="flex items-center space-x-2">
                            <Checkbox
                                id={param.id}
                                checked={params[param.id]}
                                onCheckedChange={(c) => handleCheckedChange(param.id, c)}
                            />
                            <Tooltip content={getLabel(param, 'tooltip', language)}>
                                <Label htmlFor={param.id} className="cursor-help">
                                    {getLabel(param, 'label', language)}
                                </Label>
                            </Tooltip>
                        </div>
                    ))}
                </div>
            )}

            {/* Other checkboxes */}
            {otherCheckboxes.map(param => (
                <div key={param.id} className="flex items-center space-x-2">
                    <Checkbox
                        id={param.id}
                        checked={params[param.id]}
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
                    <Label className="text-base font-semibold">{language === 'es' ? 'Colores' : 'Colors'}</Label>
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
