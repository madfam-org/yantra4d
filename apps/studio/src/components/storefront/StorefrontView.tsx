import React, { useState, useCallback } from 'react'
import { Download, Share2, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useManifest } from '../../contexts/project/ManifestProvider'
import { useProject } from '../../contexts/project/ProjectProvider'
import { apiFetch } from '../../services/core/apiClient'
import { getApiBase } from '../../services/core/backendDetection'
import PresetGallery from './PresetGallery'

interface StorefrontViewProps {
    onExitStorefront?: () => void
}

export default function StorefrontView({ onExitStorefront }: StorefrontViewProps) {
    const { t } = useLanguage()
    const { manifest } = useManifest()
    const { setParams, handleGenerate, projectSlug } = useProject()

    const [activePreset, setActivePreset] = useState<string | null>(null)
    const [, setShareUrl] = useState<string | null>(null)
    const [copied, setCopied] = useState(false)

    const project = manifest?.project ?? {} as Record<string, unknown>
    const name = (typeof project.name === 'object' ? (project.name as Record<string, string>)?.en : project.name) || project.slug || ''
    const description = (typeof project.description === 'object' ? (project.description as Record<string, string>)?.en : project.description) || ''
    const tags = project.tags as string[] | undefined
    const presets = manifest?.presets ?? []
    const bom = (manifest as Record<string, unknown>)?.bom as Array<Record<string, unknown>> ?? []
    const modes = manifest?.modes ?? []
    const firstMode = modes[0]?.id ?? ''

    // Apply a preset's values to params
    const handleSelectPreset = useCallback((preset: Record<string, unknown>) => {
        setActivePreset(preset.id as string)
        setParams((prev: Record<string, unknown>) => ({ ...prev, ...(preset.values as Record<string, unknown>) }))
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
                        {tags && tags.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mt-2">
                                {tags.map((tag: string) => (
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
                                        <td className="py-2 pr-4 border-b border-border/50">{(typeof item.label === 'object' ? item.label?.en : item.label) || item.id}</td>
                                        <td className="py-2 pr-4 border-b border-border/50">{(item.qty as number) ?? 1}</td>
                                        <td className="py-2 pr-4 border-b border-border/50">
                                            {item.url
                                                ? <a href={item.url as string} target="_blank" rel="noopener noreferrer">
                                                    {(item.supplier as string) || t('bom.buy', 'Buy')}
                                                </a>
                                                : ((item.supplier as string) || '—')}
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
