import React from 'react'
import { useLanguage } from '../../contexts/LanguageProvider'
import { useManifest } from '../../contexts/ManifestProvider'

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
    const { language, t } = useLanguage()
    const { getLabel } = useManifest()

    const visiblePresets = presets.filter(p =>
        !p.modes || p.modes.includes(currentMode)
    )

    if (visiblePresets.length === 0) return null

    return (
        <div className="preset-gallery" data-testid="preset-gallery">
            <h3 className="preset-gallery__title">
                {t('storefront.presets', 'Configurations')}
            </h3>

            <div className="preset-gallery__grid">
                {visiblePresets.map(preset => {
                    const label = getLabel(preset.label) || preset.id
                    const isActive = preset.id === activePreset

                    return (
                        <button
                            key={preset.id}
                            className={`preset-card ${isActive ? 'preset-card--active' : ''}`}
                            data-testid={`preset-card-${preset.id}`}
                            onClick={() => onSelect?.(preset)}
                            aria-pressed={isActive}
                        >
                            {/* Emoji badge if present */}
                            {preset.emoji && (
                                <span className="preset-card__emoji" aria-hidden="true">
                                    {preset.emoji}
                                </span>
                            )}

                            <span className="preset-card__label">{label}</span>

                            {/* Show key parameter values as a summary */}
                            {preset.values && (
                                <ul className="preset-card__values">
                                    {Object.entries(preset.values).slice(0, 3).map(([k, v]) => (
                                        <li key={k} className="preset-card__value-item">
                                            <span className="preset-card__value-key">{k}</span>
                                            <span className="preset-card__value-val">{String(v)}</span>
                                        </li>
                                    ))}
                                </ul>
                            )}

                            {isActive && (
                                <span className="preset-card__active-badge">
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
