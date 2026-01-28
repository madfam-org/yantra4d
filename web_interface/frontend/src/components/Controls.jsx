import React from 'react'
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Checkbox } from "@/components/ui/checkbox"
import { useLanguage } from "../contexts/LanguageProvider"
import { Star } from 'lucide-react'

const DEFAULTS = {
    size: 20.0,
    thick: 2.5,
    rod_D: 3.0,
    rows: 8,
    cols: 8,
    rod_extension: 10
}

export default function Controls({ params, setParams, mode, colors, setColors }) {
    const { t } = useLanguage()

    // Generic handler for sliders (value comes as array [val])
    const handleSliderChange = (name, valArray) => {
        setParams(prev => ({ ...prev, [name]: valArray[0] }))
    }

    // Generic handler for checkboxes
    const handleCheckedChange = (name, checked) => {
        setParams(prev => ({ ...prev, [name]: checked }))
    }

    const handleColorChange = (key, val) => {
        setColors(prev => ({ ...prev, [key]: val }))
    }

    const renderSlider = (name, label, min, max, step) => {
        const value = params[name]
        const isDefault = value === DEFAULTS[name]
        return (
            <div className="space-y-2">
                <div className="flex justify-between items-center">
                    <Label className="flex items-center gap-2">
                        {label}
                        {isDefault && <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />}
                    </Label>
                    <span className="text-sm text-muted-foreground">{value}</span>
                </div>
                <Slider
                    value={[value]}
                    min={min} max={max} step={step}
                    onValueChange={(vals) => handleSliderChange(name, vals)}
                />
            </div>
        )
    }

    return (
        <div className="flex flex-col gap-6">

            {/* Unit / Assembly Mode Specific */}
            {(mode === 'unit' || mode === 'assembly') && (
                <div className="space-y-4">
                    {renderSlider('size', t("ctl.size"), 10, 50, 0.5)}
                    {renderSlider('thick', t("ctl.thick"), 1, 10, 0.1)}
                    {renderSlider('rod_D', t("ctl.rod_d"), 2, 10, 0.1)}

                    <div className="space-y-4 border-t border-border pt-4">
                        <Label className="text-base font-semibold">{t("ctl.vis")}</Label>
                        <div className="flex items-center space-x-2">
                            <Checkbox id="show_base" checked={params.show_base} onCheckedChange={(c) => handleCheckedChange('show_base', c)} />
                            <Label htmlFor="show_base">{t("ctl.vis.base")}</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <Checkbox id="show_walls" checked={params.show_walls} onCheckedChange={(c) => handleCheckedChange('show_walls', c)} />
                            <Label htmlFor="show_walls">{t("ctl.vis.walls")}</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                            <Checkbox id="show_mech" checked={params.show_mech} onCheckedChange={(c) => handleCheckedChange('show_mech', c)} />
                            <Label htmlFor="show_mech">{t("ctl.vis.mech")}</Label>
                        </div>
                    </div>
                </div>
            )}

            {/* Grid Mode Specific */}
            {mode === 'grid' && (
                <div className="space-y-4">
                    <h3 className="text-sm font-medium text-muted-foreground">{t("ctl.grid.dim")}</h3>
                    {renderSlider('rows', t("ctl.rows"), 1, 20, 1)}
                    {renderSlider('cols', t("ctl.cols"), 1, 20, 1)}

                    <div className="space-y-2">
                        {renderSlider('rod_extension', t("ctl.rod_ext"), 0, 50, 1)}
                        <p className="text-xs text-muted-foreground">{t("ctl.rod_ext_desc")}</p>
                    </div>
                </div>
            )}

            {/* Color Controls (Global) */}
            <div className="space-y-4 border-t border-border pt-4">
                <Label className="text-base font-semibold">Colors</Label>
                <div className="grid grid-cols-2 gap-2">
                    <div className="flex flex-col gap-1">
                        <Label className="text-xs">Bottom Unit</Label>
                        <input type="color" className="w-full h-8 cursor-pointer" value={colors.bottom} onChange={(e) => handleColorChange('bottom', e.target.value)} />
                    </div>
                    <div className="flex flex-col gap-1">
                        <Label className="text-xs">Top Unit</Label>
                        <input type="color" className="w-full h-8 cursor-pointer" value={colors.top} onChange={(e) => handleColorChange('top', e.target.value)} />
                    </div>
                    <div className="flex flex-col gap-1">
                        <Label className="text-xs">Rods</Label>
                        <input type="color" className="w-full h-8 cursor-pointer" value={colors.rods} onChange={(e) => handleColorChange('rods', e.target.value)} />
                    </div>
                    <div className="flex flex-col gap-1">
                        <Label className="text-xs">Stoppers</Label>
                        <input type="color" className="w-full h-8 cursor-pointer" value={colors.stoppers} onChange={(e) => handleColorChange('stoppers', e.target.value)} />
                    </div>
                </div>
            </div>
        </div>
    )
}
