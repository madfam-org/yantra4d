import React from 'react'
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Checkbox } from "@/components/ui/checkbox"
import { useLanguage } from "../contexts/LanguageProvider"

export default function Controls({ params, setParams, mode }) {
    const { t } = useLanguage()

    // Generic handler for sliders (value comes as array [val])
    const handleSliderChange = (name, valArray) => {
        setParams(prev => ({ ...prev, [name]: valArray[0] }))
    }

    // Generic handler for checkboxes
    const handleCheckedChange = (name, checked) => {
        setParams(prev => ({ ...prev, [name]: checked }))
    }

    return (
        <div className="flex flex-col gap-6">

            {/* Unit Mode Specific */}
            {mode === 'unit' && (
                <div className="space-y-4">
                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <Label>{t("ctl.size")}</Label>
                            <span className="text-sm text-muted-foreground">{params.size}</span>
                        </div>
                        <Slider
                            value={[params.size]}
                            min={10} max={50} step={0.5}
                            onValueChange={(vals) => handleSliderChange('size', vals)}
                        />
                    </div>

                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <Label>{t("ctl.thick")}</Label>
                            <span className="text-sm text-muted-foreground">{params.thick}</span>
                        </div>
                        <Slider
                            value={[params.thick]}
                            min={1} max={10} step={0.1}
                            onValueChange={(vals) => handleSliderChange('thick', vals)}
                        />
                    </div>

                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <Label>{t("ctl.rod_d")}</Label>
                            <span className="text-sm text-muted-foreground">{params.rod_D}</span>
                        </div>
                        <Slider
                            value={[params.rod_D]}
                            min={2} max={10} step={0.1}
                            onValueChange={(vals) => handleSliderChange('rod_D', vals)}
                        />
                    </div>

                    <div className="space-y-4 border-t border-border pt-4">
                        <Label className="text-base font-semibold">{t("ctl.vis")}</Label>

                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="show_base"
                                checked={params.show_base}
                                onCheckedChange={(c) => handleCheckedChange('show_base', c)}
                            />
                            <Label htmlFor="show_base">{t("ctl.vis.base")}</Label>
                        </div>

                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="show_walls"
                                checked={params.show_walls}
                                onCheckedChange={(c) => handleCheckedChange('show_walls', c)}
                            />
                            <Label htmlFor="show_walls">{t("ctl.vis.walls")}</Label>
                        </div>

                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="show_mech"
                                checked={params.show_mech}
                                onCheckedChange={(c) => handleCheckedChange('show_mech', c)}
                            />
                            <Label htmlFor="show_mech">{t("ctl.vis.mech")}</Label>
                        </div>
                    </div>
                </div>
            )}

            {/* Grid Mode Specific */}
            {mode === 'grid' && (
                <div className="space-y-4">
                    {/* Unit parameters hidden for strict separation */}
                    <h3 className="text-sm font-medium text-muted-foreground">{t("ctl.grid.dim")}</h3>

                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <Label>{t("ctl.rows")}</Label>
                            <span className="text-sm text-muted-foreground">{params.rows}</span>
                        </div>
                        <Slider
                            value={[params.rows]}
                            min={1} max={20} step={1}
                            onValueChange={(vals) => handleSliderChange('rows', vals)}
                        />
                    </div>

                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <Label>{t("ctl.cols")}</Label>
                            <span className="text-sm text-muted-foreground">{params.cols}</span>
                        </div>
                        <Slider
                            value={[params.cols]}
                            min={1} max={20} step={1}
                            onValueChange={(vals) => handleSliderChange('cols', vals)}
                        />
                    </div>

                    <div className="space-y-2">
                        <div className="flex justify-between">
                            <Label>{t("ctl.rod_ext")}</Label>
                            <span className="text-sm text-muted-foreground">{params.rod_extension}</span>
                        </div>
                        <Slider
                            value={[params.rod_extension]}
                            min={0} max={50} step={1}
                            onValueChange={(vals) => handleSliderChange('rod_extension', vals)}
                        />
                        <p className="text-xs text-muted-foreground">{t("ctl.rod_ext_desc")}</p>
                    </div>
                </div>
            )}
        </div>
    )
}
