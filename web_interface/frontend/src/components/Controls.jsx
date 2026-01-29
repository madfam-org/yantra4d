import React, { useState } from 'react'
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Checkbox } from "@/components/ui/checkbox"
import { useLanguage } from "../contexts/LanguageProvider"
import { Tooltip } from "@/components/ui/tooltip"
import { Star } from 'lucide-react'
import { DEFAULTS, MODE_COLORS_MAP } from '../config/defaults'

const PARAM_DEFAULTS = DEFAULTS.params

export default function Controls({ params, setParams, mode, colors, setColors }) {
    const { t } = useLanguage()

    const handleSliderChange = (name, valArray) => {
        setParams(prev => ({ ...prev, [name]: valArray[0] }))
    }

    const handleCheckedChange = (name, checked) => {
        setParams(prev => ({ ...prev, [name]: checked }))
    }

    const handleColorChange = (key, val) => {
        setColors(prev => ({ ...prev, [key]: val }))
    }

    const renderSlider = (name, label, min, max, step, tooltipKey) => {
        const value = params[name]
        const isDefault = value === PARAM_DEFAULTS[name]
        const [editing, setEditing] = useState(false)
        const [editValue, setEditValue] = useState('')

        const commitEdit = () => {
            const num = parseFloat(editValue)
            if (!isNaN(num)) {
                const clamped = Math.min(max, Math.max(min, num))
                const stepped = Math.round(clamped / step) * step
                handleSliderChange(name, [parseFloat(stepped.toFixed(4))])
            }
            setEditing(false)
        }

        return (
            <div className="space-y-2">
                <div className="flex justify-between items-center">
                    <Tooltip content={t(tooltipKey)}>
                        <Label className="flex items-center gap-2 cursor-help">
                            {label}
                            {isDefault && <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />}
                        </Label>
                    </Tooltip>
                    {editing ? (
                        <input
                            type="number"
                            className="w-16 text-sm text-right bg-input border border-border rounded px-1 py-0.5"
                            value={editValue}
                            min={min} max={max} step={step}
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
                    min={min} max={max} step={step}
                    onValueChange={(vals) => handleSliderChange(name, vals)}
                />
            </div>
        )
    }

    const colorKeys = MODE_COLORS_MAP[mode] || ['main']
    const colorLabelMap = {
        main: 'ctl.color.main',
        bottom: 'ctl.color.bottom',
        top: 'ctl.color.top',
        rods: 'ctl.color.rods',
        stoppers: 'ctl.color.stoppers',
    }

    return (
        <div className="flex flex-col gap-6">

            {/* Unit / Assembly Mode Specific */}
            {(mode === 'unit' || mode === 'assembly') && (
                <div className="space-y-4">
                    {renderSlider('size', t("ctl.size"), 10, 50, 0.5, 'tooltip.size')}
                    {renderSlider('thick', t("ctl.thick"), 1, 10, 0.1, 'tooltip.thick')}
                    {renderSlider('rod_D', t("ctl.rod_d"), 2, 10, 0.1, 'tooltip.rod_d')}

                    <div className="space-y-4 border-t border-border pt-4">
                        <Label className="text-base font-semibold">{t("ctl.vis")}</Label>
                        <div className="flex items-center space-x-2">
                            <Checkbox id="show_base" checked={params.show_base} onCheckedChange={(c) => handleCheckedChange('show_base', c)} />
                            <Tooltip content={t("tooltip.base")}>
                                <Label htmlFor="show_base" className="cursor-help">{t("ctl.vis.base")}</Label>
                            </Tooltip>
                        </div>
                        <div className="flex items-center space-x-2">
                            <Checkbox id="show_walls" checked={params.show_walls} onCheckedChange={(c) => handleCheckedChange('show_walls', c)} />
                            <Tooltip content={t("tooltip.walls")}>
                                <Label htmlFor="show_walls" className="cursor-help">{t("ctl.vis.walls")}</Label>
                            </Tooltip>
                        </div>
                        <div className="flex items-center space-x-2">
                            <Checkbox id="show_mech" checked={params.show_mech} onCheckedChange={(c) => handleCheckedChange('show_mech', c)} />
                            <Tooltip content={t("tooltip.mech")}>
                                <Label htmlFor="show_mech" className="cursor-help">{t("ctl.vis.mech")}</Label>
                            </Tooltip>
                        </div>
                    </div>
                </div>
            )}

            {/* Grid Mode Specific */}
            {mode === 'grid' && (
                <div className="space-y-4">
                    <h3 className="text-sm font-medium text-muted-foreground">{t("ctl.grid.dim")}</h3>
                    {renderSlider('rows', t("ctl.rows"), 1, 20, 1, 'tooltip.rows')}
                    {renderSlider('cols', t("ctl.cols"), 1, 20, 1, 'tooltip.cols')}

                    <div className="space-y-2">
                        {renderSlider('rod_extension', t("ctl.rod_ext"), 0, 50, 1, 'tooltip.rod_ext')}
                        <p className="text-xs text-muted-foreground">{t("ctl.rod_ext_desc")}</p>
                    </div>
                </div>
            )}

            {/* Color Controls — mode-filtered */}
            <div className="space-y-4 border-t border-border pt-4">
                <Label className="text-base font-semibold">{t("ctl.colors")}</Label>
                <div className={`grid gap-2 ${colorKeys.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
                    {colorKeys.map((key) => (
                        <div key={key} className="flex flex-col gap-1">
                            <Label className="text-xs">{t(colorLabelMap[key])}</Label>
                            <input
                                type="color"
                                className="w-full h-8 cursor-pointer"
                                value={colors[key] || '#e5e7eb'}
                                onChange={(e) => handleColorChange(key, e.target.value)}
                            />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
