import React, { useState, useCallback } from 'react'
import { Download, Share2, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useManifest } from '../../contexts/project/ManifestProvider'
import { useProject } from '../../contexts/project/ProjectProvider'
import { apiFetch } from '../../services/core/apiClient'
import { getApiBase } from '../../services/core/backendDetection'
import PresetGallery from './PresetGallery'

/**
 * StorefrontView — customer-facing layout for a project.
 *
 * Activated by ?mode=storefront in the URL.
 * Hides developer UI (parameter groups, SCAD info, mode IDs).
 * Shows: product name, description, preset gallery, BOM, Download CTA.
 */
export default function StorefrontView({ onExitStorefront }) {
    const { t } = useLanguage()
    const { manifest, getLabel } = useManifest()
    const { setParams, handleGenerate, projectSlug } = useProject()

    const [activePreset, setActivePreset] = useState(null)
    const [, setShareUrl] = useState(null)
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
            const res = await apiFetch(`${getApiBase()}/api/projects/${projectSlug}/share/${activePreset}`)
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
        <div className="flex flex-col min-h-dvh bg-background" data-testid="storefront-view">
            {/* Header */}
            <header className="border-b border-border bg-card px-4 py-4 sm:px-6 sm:py-6">
                <div className="flex items-start justify-between gap-4 max-w-4xl mx-auto">
                    <div>
                        <h1 className="text-xl sm:text-2xl md:text-3xl font-bold tracking-tight" data-testid="storefront-title">
                            {name}
                        </h1>
                        {description && (
                            <p className="text-sm sm:text-base text-muted-foreground mt-1">{description}</p>
                        )}
                        {project.tags?.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mt-2">
                                {project.tags.map(tag => (
                                    <span key={tag} className="text-xs bg-muted px-2 py-0.5 rounded-full text-muted-foreground">#{tag}</span>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Exit storefront (dev shortcut) */}
                    {onExitStorefront && (
                        <button
                            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground min-h-[44px] min-w-[44px] justify-center"
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

            <main className="flex-1 px-4 py-6 sm:px-6 sm:py-8 max-w-4xl mx-auto w-full space-y-8">
                {/* Preset Gallery */}
                {presets.length > 0 && (
                    <section>
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
                    <section data-testid="storefront-bom">
                        <h2 className="text-lg font-semibold mb-3">
                            {t('storefront.bom', 'Bill of Materials')}
                        </h2>
                        <table className="w-full text-sm border-collapse">
                            <thead>
                                <tr>
                                    <th className="text-left text-xs text-muted-foreground py-2 pr-4 border-b border-border">{t('bom.part', 'Part')}</th>
                                    <th className="text-left text-xs text-muted-foreground py-2 pr-4 border-b border-border">{t('bom.qty', 'Qty')}</th>
                                    <th className="text-left text-xs text-muted-foreground py-2 pr-4 border-b border-border">{t('bom.supplier', 'Supplier')}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {bom.map((item, i) => (
                                    <tr key={i}>
                                        <td className="py-2 pr-4 border-b border-border/50">{getLabel(item.label) || item.id}</td>
                                        <td className="py-2 pr-4 border-b border-border/50">{item.qty ?? 1}</td>
                                        <td className="py-2 pr-4 border-b border-border/50">
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
                <section className="flex flex-col sm:flex-row gap-3">
                    <Button
                        onClick={handleGenerate}
                        className="gap-2 min-h-[44px]"
                        data-testid="storefront-generate"
                    >
                        <Download size={16} />
                        {t('storefront.downloadStl', 'Download STL')}
                    </Button>

                    {activePreset && (
                        <Button
                            variant="outline"
                            onClick={handleShare}
                            className="gap-2 min-h-[44px]"
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
