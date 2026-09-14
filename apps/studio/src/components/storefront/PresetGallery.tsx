import React from 'react'
import { useLanguage } from '../../contexts/system/LanguageProvider'

interface Preset {
    id: string
    values?: Record<string, unknown>
    emoji?: string
    visible_in_modes?: string[]
    [key: string]: unknown
}

interface PresetGalleryProps {
    presets?: Preset[] | Array<Record<string, unknown>>
    currentMode: string
    onSelect?: (preset: Record<string, unknown>) => void
    activePreset?: string | null
    /** Parameter ids to show first in a card's three-value summary (the manifest's
     *  first parameter group — the envelope for a device cartridge — instead of
     *  whichever keys sort first). Unknown ids are ignored. */
    summaryKeys?: string[]
}

/** Order a preset's values so `summaryKeys` come first (in that order), then the rest. */
export function summaryEntries(values: Record<string, unknown>, summaryKeys: string[] = []): Array<[string, unknown]> {
    const entries = Object.entries(values)
    if (summaryKeys.length === 0) return entries
    const rank = new Map(summaryKeys.map((k, i) => [k, i]))
    return [...entries].sort((a, b) => {
        const ra = rank.has(a[0]) ? (rank.get(a[0]) as number) : Number.MAX_SAFE_INTEGER
        const rb = rank.has(b[0]) ? (rank.get(b[0]) as number) : Number.MAX_SAFE_INTEGER
        return ra - rb
    })
}

export default function PresetGallery({ presets = [], currentMode, onSelect, activePreset, summaryKeys = [] }: PresetGalleryProps) {
    const { t } = useLanguage()

    const visiblePresets = (presets as Preset[]).filter(p =>
        !p.visible_in_modes || p.visible_in_modes.includes(currentMode)
    )

    if (visiblePresets.length === 0) return null

    return (
        <div data-testid="preset-gallery">
            <h3 className="text-lg font-semibold mb-3">
                {t('storefront.presets', 'Configurations')}
            </h3>

            <div className="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-3 gap-3">
                {visiblePresets.map(preset => {
                    const rawLabel = preset.label
                    const label = (typeof rawLabel === 'object' && rawLabel !== null ? (rawLabel as Record<string, string>).en : rawLabel) || preset.id
                    const isActive = preset.id === activePreset

                    return (
                        <button
                            key={preset.id}
                            className={`flex flex-col items-start gap-2 p-4 rounded-lg border bg-card hover:border-primary/50 transition-colors cursor-pointer min-h-[44px] text-left ${isActive ? 'border-primary bg-primary/5 ring-2 ring-primary/20' : 'border-border'}`}
                            data-testid={`preset-card-${preset.id}`}
                            onClick={() => onSelect?.(preset)}
                            aria-pressed={isActive}
                        >
                            {/* Emoji badge if present */}
                            {preset.emoji && (
                                <span className="text-2xl" aria-hidden="true">
                                    {preset.emoji}
                                </span>
                            )}

                            <span className="font-medium text-sm">{label}</span>

                            {/* Show key parameter values as a summary */}
                            {preset.values && (
                                <ul className="list-none p-0 m-0 space-y-0.5 w-full">
                                    {summaryEntries(preset.values, summaryKeys).slice(0, 3).map(([k, v]) => (
                                        <li key={k} className="flex justify-between text-xs text-muted-foreground">
                                            <span className="font-mono opacity-70">{k}</span>
                                            <span className="font-medium text-foreground">{String(v)}</span>
                                        </li>
                                    ))}
                                </ul>
                            )}

                            {isActive && (
                                <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                                    {t('storefront.active', 'Active')}
                                </span>
                            )}
                        </button>
                    )
                })}
            </div>
        </div>
    )
}
