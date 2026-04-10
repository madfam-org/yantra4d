import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion"
import { Download, FileCode, FileText, Copy, Check, Link2, Archive, Clock, Weight, DollarSign } from 'lucide-react'
import { useLanguage } from "../../contexts/system/LanguageProvider"
import { useManifest } from "../../contexts/project/ManifestProvider"
import { useProject } from "../../contexts/project/ProjectProvider"
import { getApiBase } from "../../services/core/backendDetection"
import { useTier } from "../../hooks/system/useTier"
import { useUpgradePrompt } from '../../hooks/system/useUpgradePrompt'
import AuthGate from "../auth/AuthGate"
import { downloadZip } from '../../lib/downloadUtils'

const EXPORT_FORMATS = [
  { id: 'stl', label: 'STL', ext: '.stl' },
  { id: '3mf', label: '3MF', ext: '.3mf' },
  { id: 'off', label: 'OFF', ext: '.off' },
  { id: 'step', label: 'STEP', ext: '.step' },
  { id: 'glb', label: 'GLB', ext: '.glb' },
  { id: 'gltf', label: 'GLTF', ext: '.gltf' },
  { id: 'obj', label: 'OBJ', ext: '.obj' },
]

interface ExportPanelProps {
  manifest?: Record<string, unknown>
  parts: Array<{ url?: string; download_url?: string; type?: string }>
  mode: string
  onDownloadStl: () => void
  onExportImage: (viewId: string) => void
  onExportAllViews: () => void
  exportFormat?: string
  onExportFormatChange?: (format: string) => void
}

export default function ExportPanel({ manifest: propManifest, parts, mode, onDownloadStl, onExportImage, onExportAllViews, exportFormat, onExportFormatChange }: ExportPanelProps) {
  const { language, t } = useLanguage()
  const { getCameraViews, getLabel, manifest: contextManifest } = useManifest()
  const { printEstimate, copyShareUrl, params, projectSlug } = useProject()
  const manifest = propManifest || contextManifest
  const cameraViews = getCameraViews()
  const disabled = parts.length === 0

  const [estimateCopied, setEstimateCopied] = useState(false)
  const [shareCopied, setShareCopied] = useState(false)
  const [archiving, setArchiving] = useState(false)

  // Derive expected part count from manifest so label is correct before first render
  const modeConfig = (manifest as Record<string, unknown>)?.modes ? ((manifest as Record<string, unknown>).modes as Array<Record<string, unknown>>)?.find(m => m.id === mode) : undefined
  const expectedPartCount = (modeConfig?.parts as string[] | undefined)?.length || 0
  const isZip = expectedPartCount > 1

  // Supported formats from manifest or defaults
  const supportedFormats = (manifest as Record<string, unknown>)?.export_formats
    ? EXPORT_FORMATS.filter(f => ((manifest as Record<string, unknown>).export_formats as string[]).includes(f.id))
    : EXPORT_FORMATS.filter(f => f.id === 'stl')

  const { limits } = useTier()
  const userAllowedFormats = (limits as Record<string, unknown>)?.export_formats as string[] || ['stl']
  const { triggerUpgradePrompt } = useUpgradePrompt()

  const slug = (manifest as Record<string, unknown>)?.project ? ((manifest as Record<string, unknown>).project as Record<string, unknown>)?.slug as string : projectSlug

  const hasDocuments = !!((manifest as Record<string, unknown>)?.bom || (manifest as Record<string, unknown>)?.assembly_steps)
  const pe = printEstimate as Record<string, unknown> | null
  const hasPrintEstimate = (manifest as Record<string, unknown>)?.print_estimation
    ? ((manifest as Record<string, unknown>).print_estimation as Record<string, unknown>)?.enabled !== false
      && parts.length > 0 && printEstimate != null
    : parts.length > 0 && printEstimate != null

  // Build param query string for BOM CSV
  const paramQueryString = params
    ? Object.entries(params as Record<string, unknown>).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join('&')
    : ''

  function handleDownloadScad() {
    const scadFile = modeConfig?.scad_file as string | undefined
    if (slug && scadFile) {
      window.open(`${getApiBase()}/api/projects/${slug}/download/scad/${scadFile}`, '_blank')
    }
  }

  function handleDownloadBomCsv() {
    if (slug) {
      const qs = paramQueryString ? `format=csv&${paramQueryString}` : 'format=csv'
      window.open(`${getApiBase()}/api/projects/${slug}/bom?${qs}`, '_blank')
    }
  }

  async function handleCopyEstimate() {
    if (!pe) return
    const lines: string[] = []
    if (pe.time) lines.push(`${t('export.est_time')}: ${pe.time}`)
    if (pe.weight) lines.push(`${t('export.est_weight')}: ${pe.weight}`)
    if (pe.cost) lines.push(`${t('export.est_cost')}: ${pe.cost}`)
    await navigator.clipboard.writeText(lines.join('\n'))
    setEstimateCopied(true)
    setTimeout(() => setEstimateCopied(false), 2000)
  }

  async function handleCopyShareLink() {
    if (copyShareUrl) {
      await copyShareUrl()
      setShareCopied(true)
      setTimeout(() => setShareCopied(false), 2000)
    }
  }

  async function handleDownloadArchive() {
    if (!slug || parts.length === 0) return
    setArchiving(true)
    try {
      const items: Array<{ url: string; filename: string }> = []
      // Add part STLs
      parts.forEach((part, i) => {
        const fileUrl = part.download_url || part.url
        if (fileUrl) {
          const ext = exportFormat || 'stl'
          items.push({ url: fileUrl, filename: `${part.type || `part-${i}`}.${ext}` })
        }
      })
      // Add manifest JSON
      const manifestUrl = `${getApiBase()}/api/projects/${slug}/manifest`
      items.push({ url: manifestUrl, filename: 'project.json' })
      // Add BOM CSV if available
      if ((manifest as Record<string, unknown>)?.bom) {
        const bomUrl = `${getApiBase()}/api/projects/${slug}/bom?format=csv`
        items.push({ url: bomUrl, filename: 'bom.csv' })
      }
      await downloadZip(items, `${slug}-archive.zip`)
    } finally {
      setArchiving(false)
    }
  }

  // Determine default open sections
  const defaultSections = ['geometry']

  const assemblySteps = (manifest as Record<string, unknown>)?.assembly_steps as unknown[] | undefined

  return (
    <div data-testid="export-panel" className="flex flex-col border-t border-border pt-2">
      <Accordion type="multiple" defaultValue={defaultSections}>
        {/* Section A: Geometry */}
        <AccordionItem value="geometry">
          <AccordionTrigger className="text-sm min-h-[44px] py-3">
            {t('export.geometry')}
          </AccordionTrigger>
          <AccordionContent className="space-y-2">
            {supportedFormats.length > 1 && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">{t("act.format")}:</span>
                <div className="flex gap-1 flex-wrap">
                  {supportedFormats.map(f => {
                    const isLocked = !userAllowedFormats.includes(f.id)
                    return (
                      <button
                        key={f.id}
                        type="button"
                        title={isLocked ? t("tier.pro_required") : undefined}
                        className={`px-2 py-2 min-h-[44px] min-w-[44px] rounded text-xs border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1
                        ${isLocked ? 'hover:bg-muted text-muted-foreground border-border' :
                            (exportFormat || 'stl') === f.id
                              ? 'bg-primary text-primary-foreground border-primary'
                              : 'bg-background text-muted-foreground border-border hover:text-foreground'
                          }`}
                        onClick={() => {
                          if (isLocked) {
                            triggerUpgradePrompt(`Premium Export Formats (${f.label})`)
                          } else {
                            onExportFormatChange?.(f.id)
                          }
                        }}
                      >
                        {f.label} {isLocked && "\uD83D\uDD12"}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            <AuthGate
              action="download_stl"
              fallback={
                <Button variant="outline" disabled className="w-full gap-2 opacity-60">
                  <Download className="h-4 w-4" />
                  {t("auth.sign_in_to_download")}
                </Button>
              }
            >
              <Button
                variant="outline"
                onClick={onDownloadStl}
                disabled={disabled}
                className="w-full gap-2 min-h-[44px]"
                title={disabled ? t("export.no_parts") : t("tooltip.download")}
              >
                <Download className="h-4 w-4" />
                {t("act.download")} {(exportFormat || 'stl').toUpperCase()}{isZip ? ' (ZIP)' : ''}
              </Button>
            </AuthGate>

            <AuthGate
              action="download_scad"
              fallback={
                <Button variant="outline" disabled className="w-full gap-2 opacity-60">
                  <FileCode className="h-4 w-4" />
                  {t("auth.sign_in_to_download")}
                </Button>
              }
            >
              <Button
                variant="outline"
                onClick={handleDownloadScad}
                disabled={!modeConfig?.scad_file}
                className="w-full gap-2 min-h-[44px]"
                title={!modeConfig?.scad_file ? t("export.no_parts") : undefined}
              >
                <FileCode className="h-4 w-4" />
                {t("act.download_scad")}
              </Button>
            </AuthGate>
          </AccordionContent>
        </AccordionItem>

        {/* Section B: Images */}
        <AccordionItem value="images">
          <AccordionTrigger className="text-sm min-h-[44px] py-3">
            {t('export.images')}
          </AccordionTrigger>
          <AccordionContent className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              {cameraViews.map((view: Record<string, unknown>) => (
                <Button key={view.id as string} variant="outline" size="sm" className="min-h-[44px]" onClick={() => onExportImage(view.id as string)} disabled={disabled} title={disabled ? t("export.no_parts") : undefined}>
                  {getLabel(view as never, 'label', language)}
                </Button>
              ))}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={onExportAllViews}
              disabled={disabled}
              className="w-full min-h-[44px]"
              title={disabled ? t("export.no_parts") : undefined}
            >
              {t("act.export_all")}
            </Button>
          </AccordionContent>
        </AccordionItem>

        {/* Section C: Documents (conditional) */}
        {hasDocuments && (
          <AccordionItem value="documents">
            <AccordionTrigger className="text-sm min-h-[44px] py-3">
              {t('export.documents')}
            </AccordionTrigger>
            <AccordionContent className="space-y-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (slug) window.open(`${getApiBase()}/api/projects/${slug}/datasheet?lang=${language}`, '_blank')
                }}
                className="w-full min-h-[44px] gap-2"
              >
                <FileText className="h-4 w-4" />
                {t("datasheet.generate")}
              </Button>

              {(manifest as Record<string, unknown>)?.bom && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadBomCsv}
                  className="w-full min-h-[44px] gap-2"
                >
                  <Download className="h-4 w-4" />
                  {t("export.bom_csv")}
                </Button>
              )}

              {assemblySteps && assemblySteps.length > 0 && (
                <p className="text-xs text-muted-foreground px-1">
                  {t("export.assembly_count").replace('{count}', String(assemblySteps.length))}
                </p>
              )}
            </AccordionContent>
          </AccordionItem>
        )}

        {/* Section D: Print Estimate (conditional) */}
        {hasPrintEstimate && (
          <AccordionItem value="estimate">
            <AccordionTrigger className="text-sm min-h-[44px] py-3">
              {t('export.print_estimate')}
            </AccordionTrigger>
            <AccordionContent className="space-y-2">
              <div className="grid grid-cols-3 gap-2 text-xs">
                {pe?.time && (
                  <div className="flex flex-col items-center gap-1 p-2 rounded bg-muted/50">
                    <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="font-medium">{pe.time as string}</span>
                    <span className="text-muted-foreground">{t('export.est_time')}</span>
                  </div>
                )}
                {pe?.weight && (
                  <div className="flex flex-col items-center gap-1 p-2 rounded bg-muted/50">
                    <Weight className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="font-medium">{pe.weight as string}</span>
                    <span className="text-muted-foreground">{t('export.est_weight')}</span>
                  </div>
                )}
                {pe?.cost && (
                  <div className="flex flex-col items-center gap-1 p-2 rounded bg-muted/50">
                    <DollarSign className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="font-medium">{pe.cost as string}</span>
                    <span className="text-muted-foreground">{t('export.est_cost')}</span>
                  </div>
                )}
              </div>
              {(pe?.material || pe?.infill) && (
                <div className="text-xs text-muted-foreground px-1">
                  {pe.material && <span>{t('print.material')}: {pe.material as string}</span>}
                  {pe.material && pe.infill && <span> &middot; </span>}
                  {pe.infill && <span>{t('print.infill')}: {pe.infill as string}</span>}
                </div>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyEstimate}
                className="w-full min-h-[44px] gap-2"
              >
                {estimateCopied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {estimateCopied ? t("export.copied") : t("export.copy_estimate")}
              </Button>
            </AccordionContent>
          </AccordionItem>
        )}

        {/* Section E: Share & Archive */}
        <AccordionItem value="share">
          <AccordionTrigger className="text-sm min-h-[44px] py-3">
            {t('export.share')}
          </AccordionTrigger>
          <AccordionContent className="space-y-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyShareLink}
              className="w-full min-h-[44px] gap-2"
            >
              {shareCopied ? <Check className="h-4 w-4" /> : <Link2 className="h-4 w-4" />}
              {shareCopied ? t("export.copied") : t("export.share_link")}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleDownloadArchive}
              disabled={disabled || archiving}
              className="w-full min-h-[44px] gap-2"
              title={disabled ? t("export.no_parts") : t("export.archive_desc")}
            >
              <Archive className="h-4 w-4" />
              {archiving ? t("btn.proc") : t("export.archive")}
            </Button>
            <p className="text-xs text-muted-foreground px-1">
              {t("export.archive_desc")}
            </p>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  )
}
