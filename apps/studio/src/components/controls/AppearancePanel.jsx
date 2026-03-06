import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { useLanguage } from "../../contexts/system/LanguageProvider"
import { useManifest } from "../../contexts/project/ManifestProvider"

import SliderControl from './SliderControl'

export default function AppearancePanel({ mode, colors, setColors, wireframe, setWireframe, boundingBox, setBoundingBox, clippingEnabled, setClippingEnabled, clippingAxis, setClippingAxis, clippingPosition, setClippingPosition, measureMode, setMeasureMode, measurements, setMeasurements, explodeFactor, setExplodeFactor, lightIntensity, setLightIntensity, environmentPreset, setEnvironmentPreset, partsCount = 0, overhangEnabled, setOverhangEnabled, overhangThreshold, setOverhangThreshold }) {
    const { language, t } = useLanguage()
    const { getPartColors, getLabel } = useManifest()

    const partColors = getPartColors(mode)

    const handleColorChange = (key, val) => {
        setColors(prev => ({ ...prev, [key]: val }))
    }

    return (
        <div className="flex flex-col gap-6 pt-2">

            {/* Display Modes */}
            <div className="space-y-4">
                <Label className="text-base font-semibold">{t('ctrl.display')}</Label>

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

                <div className="flex items-center justify-between">
                    <Label htmlFor="bounds-toggle" className="text-sm">
                        {t('ctrl.bounds')}
                    </Label>
                    <Switch
                        id="bounds-toggle"
                        checked={boundingBox}
                        onCheckedChange={setBoundingBox}
                        aria-label={t('ctrl.bounds')}
                    />
                </div>

                {/* Exploded View (only for multi-part) */}
                {partsCount > 1 && (
                    <div className="space-y-2 pt-2 border-t border-border/50">
                        <Label className="text-sm">{t('ctrl.explode')}</Label>
                        <SliderControl
                            param={{ id: 'explode_factor', type: 'slider', min: 0, max: 2, step: 0.1, label: { en: t('ctrl.explode_factor') } }}
                            value={explodeFactor}
                            onSliderChange={(_, val) => setExplodeFactor(val[0])}
                            getLabel={getLabel}
                            language={language}
                            t={t}
                        />
                    </div>
                )}
            </div>

            {/* Analysis Tools */}
            <div className="space-y-4 border-t border-border pt-4">
                <Label className="text-base font-semibold">{t('ctrl.analysis_tools')}</Label>

                {/* Cross-Section Clipping */}
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <Label htmlFor="clipping-toggle" className="text-sm">
                            {t('ctrl.clipping')}
                        </Label>
                        <Switch
                            id="clipping-toggle"
                            checked={clippingEnabled}
                            onCheckedChange={setClippingEnabled}
                            aria-label={t('ctrl.clipping')}
                        />
                    </div>
                    {clippingEnabled && (
                        <div className="space-y-2 pl-2">
                            <div className="flex gap-1">
                                {['x', 'y', 'z'].map(a => (
                                    <button
                                        key={a}
                                        type="button"
                                        className={`flex-1 px-2 py-1 text-xs rounded border transition-colors min-h-[44px] md:min-h-0 ${clippingAxis === a
                                            ? 'bg-primary text-primary-foreground border-primary'
                                            : 'bg-background border-border hover:border-primary/50'
                                            }`}
                                        onClick={() => setClippingAxis(a)}
                                        aria-pressed={clippingAxis === a}
                                    >
                                        {a.toUpperCase()}
                                    </button>
                                ))}
                            </div>
                            <SliderControl
                                param={{ id: 'clipping_position', type: 'slider', min: 0, max: 1, step: 0.01, label: { en: t('ctrl.clipping_position') } }}
                                value={clippingPosition}
                                onSliderChange={(_, val) => setClippingPosition(val[0])}
                                getLabel={getLabel}
                                language={language}
                                t={t}
                            />
                        </div>
                    )}
                </div>

                {/* Measure Tool */}
                <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <Label htmlFor="measure-toggle" className="text-sm">
                        {t('ctrl.measure')}
                    </Label>
                    <div className="flex items-center gap-2">
                        {measureMode && measurements?.length > 0 && (
                            <button
                                type="button"
                                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                                onClick={() => setMeasurements([])}
                            >
                                {t('ctrl.measure_clear')}
                            </button>
                        )}
                        <Switch
                            id="measure-toggle"
                            checked={measureMode}
                            onCheckedChange={setMeasureMode}
                            aria-label={t('ctrl.measure')}
                        />
                    </div>
                </div>

                {/* Overhang Analysis */}
                {setOverhangEnabled && (
                    <div className="space-y-2 pt-2 border-t border-border/50">
                        <div className="flex items-center justify-between">
                            <Label htmlFor="overhang-toggle" className="text-sm">
                                {t('ctrl.overhang')}
                            </Label>
                            <Switch
                                id="overhang-toggle"
                                checked={overhangEnabled}
                                onCheckedChange={setOverhangEnabled}
                                aria-label={t('ctrl.overhang')}
                            />
                        </div>
                        {overhangEnabled && setOverhangThreshold && (
                            <div className="pl-2">
                                <SliderControl
                                    param={{ id: 'overhang_threshold', type: 'slider', min: 20, max: 80, step: 1, label: { en: t('ctrl.overhang_threshold') } }}
                                    value={overhangThreshold}
                                    onSliderChange={(_, val) => setOverhangThreshold(val[0])}
                                    getLabel={getLabel}
                                    language={language}
                                    t={t}
                                />
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Lighting Controls */}
            <div className="space-y-2 border-t border-border pt-4">
                <Label className="text-base font-semibold">{t('ctrl.lighting')}</Label>
                <SliderControl
                    param={{ id: 'light_intensity', type: 'slider', min: 0.1, max: 2, step: 0.1, label: { en: t('ctrl.brightness') } }}
                    value={lightIntensity}
                    onSliderChange={(_, val) => setLightIntensity(val[0])}
                    getLabel={getLabel}
                    language={language}
                    t={t}
                />
                <div className="space-y-1">
                    <Label htmlFor="env-preset" className="text-xs">{t('ctrl.environment')}</Label>
                    <select
                        id="env-preset"
                        className="w-full px-3 py-2 text-base md:text-sm min-h-[44px] rounded-md border border-border bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        value={environmentPreset}
                        onChange={(e) => setEnvironmentPreset(e.target.value)}
                    >
                        <option value="city">City</option>
                        <option value="warehouse">Warehouse</option>
                        <option value="studio">Studio</option>
                        <option value="sunset">Sunset</option>
                        <option value="night">Night</option>
                    </select>
                </div>
            </div>

            {/* Color Controls */}
            {partColors.length > 0 && (
                <div className="space-y-4 border-t border-border pt-4">
                    <Label className="text-base font-semibold">{t('ctrl.colors')}</Label>
                    <div className={`grid gap-2 ${partColors.length > 1 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1'}`}>
                        {partColors.map((part) => (
                            <div key={part.id} className="flex flex-col gap-1">
                                <Label htmlFor={`color-${part.id}`} className="text-xs">{getLabel(part, 'label', language)}</Label>
                                <input
                                    id={`color-${part.id}`}
                                    type="color"
                                    className="w-full h-11 min-h-[44px] cursor-pointer"
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
