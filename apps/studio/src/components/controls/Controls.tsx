import { useState, useEffect, useCallback } from 'react'
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Switch } from "@/components/ui/switch"
import { useLanguage } from "../../contexts/system/LanguageProvider"
import { useManifest } from "../../contexts/project/ManifestProvider"
import { useUnitSystem } from "../../hooks/system/useUnitSystem"
import { Tooltip } from "@/components/ui/tooltip"
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion"
import { apiFetch } from '../../services/core/apiClient'
import { getApiBase } from '../../services/core/backendDetection'

import SliderControl from './SliderControl'
import ColorGradientControl from './ColorGradientControl'
import TpmsTopologyControl from './TpmsTopologyControl'
import EnergySliderControl from './EnergySliderControl'

interface MaterialData {
    material: {
        slug: string
        am_technology: string
        vendor: string
        name: string
        [key: string]: unknown
    }
    thermodynamics?: {
        glass_transition_temp?: number
        melting_temp?: number
        [key: string]: unknown
    }
    tda?: {
        euler_characteristic: number
        persistent_homology: {
            betti_0: number
            betti_1: number
            betti_2: number
        }
    }
    semantic_ontology?: {
        iso_52900_category: string
        emmo_class: string
    }
    [key: string]: unknown
}

interface ConstraintViolation {
    severity: string
    message: string | Record<string, string>
}

interface Preset {
    id: string
    values: Record<string, unknown>
    mode?: string
    visible_in_modes?: string[]
    svg?: string
    [key: string]: unknown
}

interface ManifestParam {
    id: string
    type: string
    group?: string
    parent?: string
    visibility_level?: string
    widget?: {
        type: string
        catalog?: string
        [key: string]: unknown
    }
    maxlength?: number
    [key: string]: unknown
}

// ---------------------------------------------------------------------------
// MaterialPickerWidget
// ---------------------------------------------------------------------------
interface MaterialPickerWidgetProps {
    params: Record<string, unknown>
    setParams: (updater: (prev: Record<string, unknown>) => Record<string, unknown>, options?: { history?: boolean }) => void
    materials: MaterialData[]
    setMaterials: React.Dispatch<React.SetStateAction<MaterialData[]>>
}

function MaterialPickerWidget({ params, setParams, materials, setMaterials }: MaterialPickerWidgetProps) {
    const [loading, setLoading] = useState(false)
    const selected = (params.target_material as string) || null

    useEffect(() => {
        if (materials.length > 0) return // Skip if already loaded

        // eslint-disable-next-line react-hooks/set-state-in-effect
        setLoading(true)
        apiFetch(`${getApiBase()}/api/materials`)
            .then(r => r.json())
            .then((data: unknown) => {
                setMaterials(Array.isArray(data) ? data : [])
                setLoading(false)
            })
            .catch(() => setLoading(false))
    }, [materials.length, setMaterials])

    const handleSelect = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
        const val = e.target.value
        setParams(prev => ({ ...prev, target_material: val || undefined }))
    }, [setParams])

    const activeMaterialData = materials.find(m => m.material.slug === selected)

    return (
        <div className="space-y-4 pb-4 border-b border-border">
            <div className="space-y-2">
                <Label htmlFor="material-target" className="text-sm font-semibold flex items-center justify-between">
                    <span>Material Target</span>
                    {loading && <span className="text-xs font-normal text-muted-foreground animate-pulse">Loading...</span>}
                </Label>
                <select
                    id="material-target"
                    className="w-full px-3 py-2 text-base md:text-sm min-h-[44px] rounded-md border border-border bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    value={selected || ""}
                    onChange={handleSelect}
                >
                    <option value="">Theoretical (No Compensations)</option>
                    {materials.map(mat => {
                        const m = mat.material
                        return (
                            <option key={m.slug} value={m.slug}>
                                {m.am_technology} | {m.vendor} {m.name}
                            </option>
                        )
                    })}
                </select>
            </div>

            {/* Cognitive Visualization Array (Phase 10) */}
            {activeMaterialData?.tda && activeMaterialData?.semantic_ontology && (
                <div className="bg-muted/30 rounded-lg border border-border p-3 space-y-3 text-xs">
                    <div>
                        <span className="font-semibold block mb-1">Semantic Ontology (ISO/EMMO)</span>
                        <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-muted-foreground">
                            <span>Category:</span>
                            <span className="text-foreground text-right">{activeMaterialData.semantic_ontology.iso_52900_category}</span>
                            <span>Class URI:</span>
                            <Tooltip content={activeMaterialData.semantic_ontology.emmo_class}>
                                <span className="text-foreground text-right truncate cursor-help">Hover to view</span>
                            </Tooltip>
                        </div>
                    </div>

                    <div className="pt-2 border-t border-border/50">
                        <span className="font-semibold block mb-1">Topological Data Analysis (TDA)</span>
                        <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-muted-foreground">
                            <span>Euler Characteristic:</span>
                            <span className="text-foreground text-right font-mono">{activeMaterialData.tda.euler_characteristic}</span>
                            <span>Betti 0 (Components):</span>
                            <span className="text-foreground text-right font-mono">{activeMaterialData.tda.persistent_homology.betti_0}</span>
                            <span>Betti 1 (Holes):</span>
                            <span className="text-foreground text-right font-mono">{activeMaterialData.tda.persistent_homology.betti_1}</span>
                            <span>Betti 2 (Voids):</span>
                            <span className="text-foreground text-right font-mono">{activeMaterialData.tda.persistent_homology.betti_2}</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

// ---------------------------------------------------------------------------
// ComponentPickerWidget
// ---------------------------------------------------------------------------
interface CatalogComponent {
    id: string
    parameters?: Record<string, unknown>
    specs?: {
        bore_diameter?: number
        [key: string]: unknown
    }
    [key: string]: unknown
}

interface ComponentPickerWidgetProps {
    param: ManifestParam
    setParams: (updater: (prev: Record<string, unknown>) => Record<string, unknown>, options?: { history?: boolean }) => void
    getLabel: (obj: Record<string, unknown> | null | undefined, key: string, lang: string) => string
    language: string
}

function ComponentPickerWidget({ param, setParams, getLabel, language }: ComponentPickerWidgetProps) {
    const catalog = param.widget?.catalog ?? ''
    const category = catalog.replace('nopscadlib/', '')
    const [components, setComponents] = useState<CatalogComponent[]>([])
    const [loading, setLoading] = useState(false)
    const [selected, setSelected] = useState<string | null>(null)

    useEffect(() => {
        if (!category) return
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setLoading(true)
        apiFetch(`${getApiBase()}/api/catalog/nopscadlib/${category}`)
            .then(r => r.json())
            .then((data: { components?: CatalogComponent[] }) => {
                setComponents(data.components ?? [])
                setLoading(false)
            })
            .catch(() => setLoading(false))
    }, [category])

    const handleSelect = useCallback((component: CatalogComponent) => {
        setSelected(component.id)
        // Apply all parameter mappings from the component
        if (component.parameters) {
            setParams(prev => ({ ...prev, ...component.parameters }))
        }
    }, [setParams])

    const label = getLabel(param as unknown as Record<string, unknown>, 'label', language)

    return (
        <div className="space-y-2" data-testid={`component-picker-${param.id}`}>
            <Label className="text-sm font-medium">{label}</Label>
            {loading && (
                <p className="text-xs text-muted-foreground">Loading catalog...</p>
            )}
            {!loading && components.length === 0 && (
                <p className="text-xs text-muted-foreground">No components found for &apos;{category}&apos;</p>
            )}
            {!loading && components.length > 0 && (
                <div className="grid grid-cols-2 gap-1.5 max-h-48 overflow-y-auto pr-1">
                    {components.map(comp => (
                        <button
                            key={comp.id}
                            type="button"
                            data-testid={`component-option-${comp.id}`}
                            className={`text-left px-2 py-2 md:py-1.5 text-xs rounded border transition-colors min-h-[44px] md:min-h-0 ${selected === comp.id
                                ? 'bg-primary text-primary-foreground border-primary'
                                : 'bg-background border-border hover:border-primary/50 hover:bg-accent'
                                }`}
                            onClick={() => handleSelect(comp)}
                            aria-pressed={selected === comp.id}
                        >
                            <span className="font-mono font-semibold">{comp.id}</span>
                            {comp.specs?.bore_diameter && (
                                <span className="block text-[10px] opacity-70">
                                    ⌀{comp.specs.bore_diameter}mm bore
                                </span>
                            )}
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}

const DEFAULT_TEXT_MAX_LENGTH = 255

interface ControlsProps {
    params: Record<string, unknown>
    setParams: (updater: (prev: Record<string, unknown>) => Record<string, unknown>, options?: { history?: boolean }) => void
    mode: string
    presets?: Preset[]
    onApplyPreset: (preset: Preset) => void
    onToggleGridPreset: () => void
    constraintsByParam?: Record<string, ConstraintViolation[]>
    onParamHover?: (paramId: string) => void
    onParamLeave?: () => void
}

export default function Controls({ params, setParams, mode, presets = [], onApplyPreset, onToggleGridPreset, constraintsByParam = {}, onParamHover, onParamLeave }: ControlsProps) {
    const { language, t } = useLanguage()
    const { manifest, getParametersForMode, getLabel, getGroupLabel } = useManifest()
    const unitSystem = useUnitSystem()

    const [materials, setMaterials] = useState<MaterialData[]>([])

    const [visibilityLevel, setVisibilityLevel] = useState(() => {
        const visGroup = manifest.parameter_groups?.find(g => g.id === 'visibility')
        return (visGroup as Record<string, unknown> & { levels?: Array<{ id: string }> })?.levels?.[0]?.id || 'basic'
    })

    const handleSliderChange = (name: string, valArray: number[], commit = true) => {
        setParams(prev => ({ ...prev, [name]: valArray[0] }), { history: commit })
    }

    const handleCheckedChange = (name: string, checked: boolean | 'indeterminate') => {
        setParams(prev => ({ ...prev, [name]: checked }))
    }



    const handleGradientChange = (name: string, gradientValue: unknown) => {
        setParams(prev => ({ ...prev, [name]: gradientValue }))
    }

    const parametersForMode = getParametersForMode(mode) as ManifestParam[]
    const sliders = parametersForMode.filter(p => p.type === 'slider' && !p.widget)
    const textInputs = parametersForMode.filter(p => p.type === 'text' && !p.widget)
    const checkboxes = parametersForMode.filter(p => p.type === 'checkbox')
    const gradientParams = parametersForMode.filter(p => p.widget?.type === 'color-gradient')
    const componentPickers = parametersForMode.filter(p => p.widget?.type === 'component-picker')
    const tpmsControls = parametersForMode.filter(p => p.widget?.type === 'tpms-topology')
    const visibilityCheckboxes = checkboxes.filter(p => p.group === 'visibility')
    const otherCheckboxes = checkboxes.filter(p => p.group !== 'visibility')

    // Filter visibility checkboxes by level
    const filteredVisibility = visibilityCheckboxes.filter(p => {
        const visGroup = manifest.parameter_groups?.find(g => g.id === 'visibility')
        const firstLevelId = (visGroup as Record<string, unknown> & { levels?: Array<{ id: string }> })?.levels?.[0]?.id || 'basic'
        if (visibilityLevel === firstLevelId) {
            return !p.visibility_level || p.visibility_level === firstLevelId
        }
        return true // higher levels show all
    })


    const hasNoParameters = parametersForMode.length === 0

    const isParentUnchecked = (param: ManifestParam) => {
        if (!param.parent) return false
        return params[param.parent] === false
    }

    const activePresetId = presets.find(p =>
        Object.entries(p.values).every(([k, v]) => params[k] === v)
    )?.id || null

    const visiblePresets = presets.filter(p => !p.visible_in_modes || p.visible_in_modes.includes(mode))

    const isMaterialAware = !!(manifest?.hyperobject as Record<string, unknown> | undefined)?.material_awareness
    const activeMaterialData = materials.find(m => m.material.slug === params.target_material)

    return (
        <div className="flex flex-col gap-6">
            {isMaterialAware && (
                <>
                    <MaterialPickerWidget params={params} setParams={setParams} materials={materials} setMaterials={setMaterials} />
                    {/* The Energy Slider automatically pulls from the lifted materials state */}
                    <EnergySliderControl
                        value={params.simulated_energy as number | undefined}
                        onChange={handleSliderChange as unknown as (name: string, value: number) => void}
                        thermodynamics={activeMaterialData?.thermodynamics || null}
                        language={language}
                    />
                </>
            )}

            {hasNoParameters && visiblePresets.length === 0 && (
                <p className="text-sm text-muted-foreground px-4 py-6 text-center">No parameters available for this mode.</p>
            )}

            {/* Size Presets */}
            {visiblePresets.length > 0 && (
                <div className="flex overflow-x-auto gap-2 pb-3 scrollbar-thin sm:no-scrollbar max-w-full">
                    {visiblePresets.map(p => (
                        <button
                            key={p.id}
                            type="button"
                            className={`flex-shrink-0 px-3 py-1.5 text-sm rounded-md border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 flex items-center justify-center whitespace-nowrap min-h-[44px] ${activePresetId === p.id
                                ? 'bg-primary text-primary-foreground border-primary'
                                : 'bg-background text-muted-foreground border-border hover:text-foreground'
                                }`}
                            onClick={() => onApplyPreset(p)}
                        >
                            {p.svg ? (
                                <>
                                    <span className="md:hidden flex items-center justify-center" dangerouslySetInnerHTML={{ __html: p.svg }} />
                                    <span className="hidden md:inline-block">{getLabel(p, 'label', language)}</span>
                                </>
                            ) : (
                                getLabel(p, 'label', language)
                            )}
                        </button>
                    ))}
                </div>
            )}

            {/* Grid Presets */}
            {mode === 'grid' && manifest.grid_presets && (() => {
                const gp = manifest.grid_presets as Record<string, { values?: Record<string, unknown>; emoji?: string; label?: Record<string, string>; [key: string]: unknown }>
                const presetKeys = Object.keys(gp).filter(k => k !== 'default')
                const activeGp = presetKeys.find(id => {
                    const v = gp[id]?.values
                    return v && Object.entries(v).every(([k, val]) => params[k] === val)
                }) || null
                return (
                    <div className="flex flex-wrap gap-2">
                        {presetKeys.map(id => (
                            <button
                                key={id}
                                type="button"
                                className={`flex-1 px-3 py-2 md:py-1.5 text-sm rounded-md border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 min-h-[44px] md:min-h-0 ${activeGp === id
                                    ? 'bg-primary text-primary-foreground border-primary'
                                    : 'bg-background text-muted-foreground border-border hover:text-foreground'
                                    }`}
                                onClick={() => activeGp !== id && onToggleGridPreset()}
                            >
                                {gp[id].emoji} {getLabel(gp[id] as unknown as Record<string, unknown>, 'label', language)}
                            </button>
                        ))}
                    </div>
                )
            })()}

            {/* Text Inputs */}
            {textInputs.length > 0 && (
                <div className="space-y-4">
                    {textInputs.map(param => (
                        <div
                            key={param.id}
                            className="space-y-1"
                            onPointerEnter={() => onParamHover?.(param.id)}
                            onPointerLeave={() => onParamLeave?.()}
                        >
                            <Tooltip content={getLabel(param as unknown as Record<string, unknown>, 'tooltip', language)}>
                                <Label htmlFor={`text-${param.id}`} className="cursor-help">{getLabel(param as unknown as Record<string, unknown>, 'label', language)}</Label>
                            </Tooltip>
                            <input
                                id={`text-${param.id}`}
                                type="text"
                                maxLength={param.maxlength || DEFAULT_TEXT_MAX_LENGTH}
                                className="w-full px-3 py-2 text-base md:text-sm min-h-[44px] rounded-md border border-border bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                value={(params[param.id] as string) ?? ''}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setParams(prev => ({ ...prev, [param.id]: e.target.value }))}
                                aria-invalid={param.maxlength && ((params[param.id] as string)?.length || 0) > param.maxlength ? 'true' : undefined}
                            />
                        </div>
                    ))}
                </div>
            )}

            {/* Sliders */}
            {sliders.length > 0 && (
                <div className="space-y-4">
                    {sliders.map(param => (
                        <div
                            key={param.id}
                            onPointerEnter={() => onParamHover?.(param.id)}
                            onPointerLeave={() => onParamLeave?.()}
                        >
                            <SliderControl
                                param={param as unknown as { id: string; type: string; min: number; max: number; step: number; default: number; star?: number; disabled?: boolean; description?: string; label?: Record<string, string> }}
                                value={params[param.id] as number | undefined}
                                onSliderChange={handleSliderChange}
                                getLabel={getLabel}
                                language={language}
                                t={t}
                                unitSystem={unitSystem}
                            />
                            {constraintsByParam[param.id]?.map((v, i) => (
                                <p key={i} className={`text-xs mt-1 ${v.severity === 'error' ? 'text-destructive' : 'text-yellow-600 dark:text-yellow-400'}`} role="alert">
                                    {typeof v.message === 'string' ? v.message : (v.message as Record<string, string>)[language] || (v.message as Record<string, string>).en || String(v.message)}
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
                        <div
                            key={param.id}
                            onPointerEnter={() => onParamHover?.(param.id)}
                            onPointerLeave={() => onParamLeave?.()}
                        >
                            <ColorGradientControl
                                param={param}
                                value={params[param.id] as { start: string; end: string } | undefined}
                                onChange={handleGradientChange}
                                getLabel={getLabel}
                                language={language}
                            />
                        </div>
                    ))}
                </div>
            )}

            {/* Component Picker Widgets (NopSCADlib) */}
            {componentPickers.length > 0 && (
                <div className="space-y-4 border-t border-border pt-4">
                    {componentPickers.map(param => (
                        <div
                            key={param.id}
                            onPointerEnter={() => onParamHover?.(param.id)}
                            onPointerLeave={() => onParamLeave?.()}
                        >
                            <ComponentPickerWidget
                                param={param}
                                setParams={setParams}
                                getLabel={getLabel}
                                language={language}
                            />
                        </div>
                    ))}
                </div>
            )}

            {/* TPMS Topology Controls */}
            {tpmsControls.length > 0 && (
                <div className="space-y-4 border-t border-border pt-4">
                    {tpmsControls.map(param => (
                        <div
                            key={param.id}
                            onPointerEnter={() => onParamHover?.(param.id)}
                            onPointerLeave={() => onParamLeave?.()}
                        >
                            <TpmsTopologyControl
                                param={param}
                                value={params[param.id] as number | undefined}
                                onChange={handleSliderChange}
                                getLabel={getLabel}
                                language={language}
                            />
                        </div>
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
                                const nextLevelDef = (visGroup as Record<string, unknown> & { levels?: Array<{ id: string; label?: Record<string, string> }> })?.levels?.find(l => l.id === nextLevel)
                                return nextLevelDef ? getLabel(nextLevelDef as unknown as Record<string, unknown>, 'label', language) : nextLevel
                            })()}
                        </button>
                    </div>
                    {filteredVisibility.map(param => {
                        const isChild = param.visibility_level === 'advanced' && param.parent
                        const disabled = isParentUnchecked(param)
                        return (
                            <div
                                key={param.id}
                                className={`flex items-center space-x-2 min-h-[44px] ${isChild ? 'ml-4' : ''}`}
                                onPointerEnter={() => onParamHover?.(param.id)}
                                onPointerLeave={() => onParamLeave?.()}
                            >
                                <Checkbox
                                    id={param.id}
                                    checked={!!params[param.id]}
                                    onCheckedChange={(c: boolean | 'indeterminate') => handleCheckedChange(param.id, c)}
                                    disabled={disabled}
                                    aria-label={getLabel(param as unknown as Record<string, unknown>, 'label', language)}
                                />
                                <Tooltip content={getLabel(param as unknown as Record<string, unknown>, 'tooltip', language)}>
                                    <Label
                                        htmlFor={param.id}
                                        className={`cursor-help ${disabled ? 'opacity-50' : ''}`}
                                    >
                                        {getLabel(param as unknown as Record<string, unknown>, 'label', language)}
                                    </Label>
                                </Tooltip>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* Other checkboxes */}
            {otherCheckboxes.map(param => (
                <div
                    key={param.id}
                    className="flex items-center space-x-2 min-h-[44px]"
                    onPointerEnter={() => onParamHover?.(param.id)}
                    onPointerLeave={() => onParamLeave?.()}
                >
                    <Checkbox
                        id={param.id}
                        checked={!!params[param.id]}
                        onCheckedChange={(c: boolean | 'indeterminate') => handleCheckedChange(param.id, c)}
                        aria-label={getLabel(param as unknown as Record<string, unknown>, 'label', language)}
                    />
                    <Tooltip content={getLabel(param as unknown as Record<string, unknown>, 'tooltip', language)}>
                        <Label htmlFor={param.id} className="cursor-help">
                            {getLabel(param as unknown as Record<string, unknown>, 'label', language)}
                        </Label>
                    </Tooltip>
                </div>
            ))}

        </div>
    )
}
