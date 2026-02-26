import React from 'react'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useManifest } from '../../contexts/project/ManifestProvider'

/**
 * PresetGallery — visual grid of preset cards for the storefront view.
 *
 * Props:
 *   presets      — array of preset objects from the manifest
 *   currentMode  — active mode id (used to filter relevant presets)
 *   onSelect     — callback(preset) when user clicks a preset card
 *   activePreset — id of the currently active preset (for highlight)
 */
export default function PresetGallery({ presets = [], currentMode, onSelect, activePreset }) {
    const { t } = useLanguage()
    const { getLabel } = useManifest()

    const visiblePresets = presets.filter(p =>
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
                    const label = getLabel(preset.label) || preset.id
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
                                    {Object.entries(preset.values).slice(0, 3).map(([k, v]) => (
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
