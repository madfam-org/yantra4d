import { useState } from 'react'
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Switch } from "@/components/ui/switch"
import { useLanguage } from "../contexts/LanguageProvider"
import { useManifest } from "../contexts/ManifestProvider"
import { Tooltip } from "@/components/ui/tooltip"

import SliderControl from './controls/SliderControl'
import ColorGradientControl from './controls/ColorGradientControl'

const DEFAULT_TEXT_MAX_LENGTH = 255

export default function Controls({ params, setParams, mode, colors, setColors, wireframe, setWireframe, presets = [], onApplyPreset, onToggleGridPreset, constraintsByParam = {} }) {
    const { language, t } = useLanguage()
    const { manifest, getParametersForMode, getPartColors, getLabel, getGroupLabel } = useManifest()
    const [visibilityLevel, setVisibilityLevel] = useState(() => {
        const visGroup = manifest.parameter_groups?.find(g => g.id === 'visibility')
        return visGroup?.levels?.[0]?.id || 'basic'
    })

    const handleSliderChange = (name, valArray) => {
        setParams(prev => ({ ...prev, [name]: valArray[0] }))
    }

    const handleCheckedChange = (name, checked) => {
        setParams(prev => ({ ...prev, [name]: checked }))
    }

    const handleColorChange = (key, val) => {
        setColors(prev => ({ ...prev, [key]: val }))
    }

    const handleGradientChange = (name, gradientValue) => {
        setParams(prev => ({ ...prev, [name]: gradientValue }))
    }

    const parametersForMode = getParametersForMode(mode)
    const sliders = parametersForMode.filter(p => p.type === 'slider' && !p.widget)
    const textInputs = parametersForMode.filter(p => p.type === 'text')
    const checkboxes = parametersForMode.filter(p => p.type === 'checkbox')
    const gradientParams = parametersForMode.filter(p => p.widget?.type === 'color-gradient')
    const visibilityCheckboxes = checkboxes.filter(p => p.group === 'visibility')
    const otherCheckboxes = checkboxes.filter(p => !p.group)

    // Filter visibility checkboxes by level
    const filteredVisibility = visibilityCheckboxes.filter(p => {
        const visGroup = manifest.parameter_groups?.find(g => g.id === 'visibility')
        const firstLevelId = visGroup?.levels?.[0]?.id || 'basic'
        if (visibilityLevel === firstLevelId) {
            return !p.visibility_level || p.visibility_level === firstLevelId
        }
        return true // higher levels show all
    })

    const partColors = getPartColors(mode)

    const hasNoParameters = parametersForMode.length === 0

    const isParentUnchecked = (param) => {
        if (!param.parent) return false
        return params[param.parent] === false
    }

    const activePresetId = presets.find(p =>
        Object.entries(p.values).every(([k, v]) => params[k] === v)
    )?.id || null

    return (
        <div className="flex flex-col gap-6">
            {hasNoParameters && presets.length === 0 && partColors.length === 0 && (
                <p className="text-sm text-muted-foreground px-4 py-6 text-center">No parameters available for this mode.</p>
            )}

            {/* Size Presets */}
            {presets.length > 0 && (
                <div className="flex gap-2">
                    {presets.map(p => (
                        <button
                            key={p.id}
                            type="button"
                            className={`flex-1 px-3 py-1.5 text-sm rounded-md border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
                                activePresetId === p.id
                                    ? 'bg-primary text-primary-foreground border-primary'
                                    : 'bg-background text-muted-foreground border-border hover:text-foreground'
                            }`}
                            onClick={() => onApplyPreset(p)}
                        >
                            {getLabel(p, 'label', language)}
                        </button>
                    ))}
                </div>
            )}

            {/* Grid Presets */}
            {mode === 'grid' && manifest.grid_presets && (() => {
                const gp = manifest.grid_presets
                const presetKeys = Object.keys(gp).filter(k => k !== 'default')
                const activeGp = presetKeys.find(id => {
                    const v = gp[id]?.values
                    return v && Object.entries(v).every(([k, val]) => params[k] === val)
                }) || null
                return (
                    <div className="flex gap-2">
                        {presetKeys.map(id => (
                            <button
                                key={id}
                                type="button"
                                className={`flex-1 px-3 py-1.5 text-sm rounded-md border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
                                    activeGp === id
                                        ? 'bg-primary text-primary-foreground border-primary'
                                        : 'bg-background text-muted-foreground border-border hover:text-foreground'
                                }`}
                                onClick={() => activeGp !== id && onToggleGridPreset()}
                            >
                                {gp[id].emoji} {getLabel(gp[id], 'label', language)}
                            </button>
                        ))}
                    </div>
                )
            })()}

            {/* Text Inputs */}
            {textInputs.length > 0 && (
                <div className="space-y-4">
                    {textInputs.map(param => (
                        <div key={param.id} className="space-y-1">
                            <Tooltip content={getLabel(param, 'tooltip', language)}>
                                <Label htmlFor={`text-${param.id}`} className="cursor-help">{getLabel(param, 'label', language)}</Label>
                            </Tooltip>
                            <input
                                id={`text-${param.id}`}
                                type="text"
                                maxLength={param.maxlength || DEFAULT_TEXT_MAX_LENGTH}
                                className="w-full px-3 py-1.5 text-sm rounded-md border border-border bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                value={params[param.id] ?? ''}
                                onChange={(e) => setParams(prev => ({ ...prev, [param.id]: e.target.value }))}
                                aria-invalid={param.maxlength && (params[param.id]?.length || 0) > param.maxlength ? 'true' : undefined}
                            />
                        </div>
                    ))}
                </div>
            )}

            {/* Sliders */}
            {sliders.length > 0 && (
                <div className="space-y-4">
                    {sliders.map(param => (
                        <div key={param.id}>
                            <SliderControl
                                param={param}
                                value={params[param.id]}
                                onSliderChange={handleSliderChange}
                                getLabel={getLabel}
                                language={language}
                                t={t}
                            />
                            {constraintsByParam[param.id]?.map((v, i) => (
                                <p key={i} className={`text-xs mt-1 ${v.severity === 'error' ? 'text-destructive' : 'text-yellow-600 dark:text-yellow-400'}`} role="alert">
                                    {typeof v.message === 'string' ? v.message : v.message[language] || v.message.en || v.message}
                                </p>
                            ))}
                        </div>
                    ))}
                </div>
            )}

            {/* Color Gradient Widgets */}
            {gradientParams.length > 0 && (
                <div className="space-y-4">
                    {gradientParams.map(param => (
                        <ColorGradientControl
                            key={param.id}
                            param={param}
                            value={params[param.id]}
                            onChange={handleGradientChange}
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
                            aria-pressed={visibilityLevel !== 'basic'}
                        >
                            {(() => {
                                const visGroup = manifest.parameter_groups?.find(g => g.id === 'visibility')
                                const nextLevel = visibilityLevel === 'basic' ? 'advanced' : 'basic'
                                const nextLevelDef = visGroup?.levels?.find(l => l.id === nextLevel)
                                return nextLevelDef ? getLabel(nextLevelDef, 'label', language) : nextLevel
                            })()}
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
                                    aria-label={getLabel(param, 'label', language)}
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
                        aria-label={getLabel(param, 'label', language)}
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
                    <div className="flex items-center justify-between">
                        <Label htmlFor="wireframe-toggle" className="text-sm">
                            {t('ctrl.wireframe')}
                        </Label>
                        <Switch
                            id="wireframe-toggle"
                            checked={wireframe}
                            onCheckedChange={setWireframe}
                            aria-label={t('ctrl.wireframe')}
                        />
                    </div>
                    <div className={`grid gap-2 ${partColors.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
                        {partColors.map((part) => (
                            <div key={part.id} className="flex flex-col gap-1">
                                <Label htmlFor={`color-${part.id}`} className="text-xs">{getLabel(part, 'label', language)}</Label>
                                <input
                                    id={`color-${part.id}`}
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
