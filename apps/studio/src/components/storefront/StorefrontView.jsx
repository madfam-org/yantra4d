import React, { useState, useCallback } from 'react'
import { Download, Share2, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useLanguage } from '../../contexts/LanguageProvider'
import { useManifest } from '../../contexts/ManifestProvider'
import { useProject } from '../../contexts/ProjectProvider'
import PresetGallery from './PresetGallery'

/**
 * StorefrontView — customer-facing layout for a project.
 *
 * Activated by ?mode=storefront in the URL.
 * Hides developer UI (parameter groups, SCAD info, mode IDs).
 * Shows: product name, description, preset gallery, BOM, Download CTA.
 */
export default function StorefrontView({ onExitStorefront }) {
    const { t, language } = useLanguage()
    const { manifest, getLabel } = useManifest()
    const { params, setParams, handleGenerate, projectSlug } = useProject()

    const [activePreset, setActivePreset] = useState(null)
    const [shareUrl, setShareUrl] = useState(null)
    const [copied, setCopied] = useState(false)

    const project = manifest?.project ?? {}
    const name = getLabel(project.name) || project.slug || ''
    const description = getLabel(project.description) || ''
    const presets = manifest?.presets ?? []
    const bom = manifest?.bom ?? []
    const modes = manifest?.modes ?? []
    const firstMode = modes[0]?.id ?? ''

    // Apply a preset's values to params
    const handleSelectPreset = useCallback((preset) => {
        setActivePreset(preset.id)
        setParams(prev => ({ ...prev, ...preset.values }))
    }, [setParams])

    // Fetch and copy share URL for the active preset
    const handleShare = useCallback(async () => {
        if (!activePreset || !projectSlug) return
        try {
            const res = await fetch(`/api/projects/${projectSlug}/share/${activePreset}`)
            const data = await res.json()
            setShareUrl(data.share_url)
            await navigator.clipboard.writeText(data.share_url)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch {
            // Fallback: copy current URL
            await navigator.clipboard.writeText(window.location.href)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        }
    }, [activePreset, projectSlug])

    return (
        <div className="storefront-view" data-testid="storefront-view">
            {/* Header */}
            <header className="storefront-view__header">
                <div className="storefront-view__header-inner">
                    <div>
                        <h1 className="storefront-view__title" data-testid="storefront-title">
                            {name}
                        </h1>
                        {description && (
                            <p className="storefront-view__description">{description}</p>
                        )}
                        {project.tags?.length > 0 && (
                            <div className="storefront-view__tags">
                                {project.tags.map(tag => (
                                    <span key={tag} className="storefront-view__tag">#{tag}</span>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Exit storefront (dev shortcut) */}
                    {onExitStorefront && (
                        <button
                            className="storefront-view__exit-btn"
                            onClick={onExitStorefront}
                            data-testid="exit-storefront"
                            title="Exit storefront preview"
                        >
                            <ExternalLink size={14} />
                            {t('storefront.exitPreview', 'Exit Preview')}
                        </button>
                    )}
                </div>
            </header>

            <main className="storefront-view__main">
                {/* Preset Gallery */}
                {presets.length > 0 && (
                    <section className="storefront-view__section">
                        <PresetGallery
                            presets={presets}
                            currentMode={firstMode}
                            onSelect={handleSelectPreset}
                            activePreset={activePreset}
                        />
                    </section>
                )}

                {/* BOM */}
                {bom.length > 0 && (
                    <section className="storefront-view__section" data-testid="storefront-bom">
                        <h2 className="storefront-view__section-title">
                            {t('storefront.bom', 'Bill of Materials')}
                        </h2>
                        <table className="storefront-view__bom-table">
                            <thead>
                                <tr>
                                    <th>{t('bom.part', 'Part')}</th>
                                    <th>{t('bom.qty', 'Qty')}</th>
                                    <th>{t('bom.supplier', 'Supplier')}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {bom.map((item, i) => (
                                    <tr key={i}>
                                        <td>{getLabel(item.label) || item.id}</td>
                                        <td>{item.qty ?? 1}</td>
                                        <td>
                                            {item.url
                                                ? <a href={item.url} target="_blank" rel="noopener noreferrer">
                                                    {item.supplier || t('bom.buy', 'Buy')}
                                                </a>
                                                : (item.supplier || '—')}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </section>
                )}

                {/* CTAs */}
                <section className="storefront-view__ctas">
                    <Button
                        onClick={handleGenerate}
                        className="storefront-view__cta-primary"
                        data-testid="storefront-generate"
                    >
                        <Download size={16} />
                        {t('storefront.downloadStl', 'Download STL')}
                    </Button>

                    {activePreset && (
                        <Button
                            variant="outline"
                            onClick={handleShare}
                            className="storefront-view__cta-share"
                            data-testid="storefront-share"
                        >
                            <Share2 size={16} />
                            {copied
                                ? t('storefront.copied', 'Link copied!')
                                : t('storefront.share', 'Share Configuration')}
                        </Button>
                    )}
                </section>
            </main>
        </div>
    )
}
