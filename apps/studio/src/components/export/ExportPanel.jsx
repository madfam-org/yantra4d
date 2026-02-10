import { Button } from "@/components/ui/button"
import { Download, FileCode, FileText } from 'lucide-react'
import { useLanguage } from "../../contexts/LanguageProvider"
import { useManifest } from "../../contexts/ManifestProvider"
import { getApiBase } from "../../services/backendDetection"
import AuthGate from "../auth/AuthGate"

const EXPORT_FORMATS = [
  { id: 'stl', label: 'STL', ext: '.stl' },
  { id: '3mf', label: '3MF', ext: '.3mf' },
  { id: 'off', label: 'OFF', ext: '.off' },
]

export default function ExportPanel({ parts, mode, onDownloadStl, onDownloadScad, onExportImage, onExportAllViews, exportFormat, onExportFormatChange }) {
  const { language, t } = useLanguage()
  const { getCameraViews, getLabel, manifest } = useManifest()
  const cameraViews = getCameraViews()
  const disabled = parts.length === 0

  // Derive expected part count from manifest so label is correct before first render
  const modeConfig = manifest?.modes?.find(m => m.id === mode)
  const expectedPartCount = modeConfig?.parts?.length || 0
  const isZip = expectedPartCount > 1

  // Supported formats from manifest or defaults
  const supportedFormats = manifest?.export_formats
    ? EXPORT_FORMATS.filter(f => manifest.export_formats.includes(f.id))
    : EXPORT_FORMATS.filter(f => f.id === 'stl')

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-4">
      {supportedFormats.length > 1 && (
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">{t("act.format")}:</span>
          <div className="flex gap-1">
            {supportedFormats.map(f => (
              <button
                key={f.id}
                type="button"
                className={`px-2 py-0.5 rounded text-xs border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 ${
                  (exportFormat || 'stl') === f.id
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background text-muted-foreground border-border hover:text-foreground'
                }`}
                onClick={() => onExportFormatChange?.(f.id)}
              >
                {f.label}
              </button>
            ))}
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
          className="w-full gap-2"
          title={disabled ? "Render model first" : t("tooltip.download")}
        >
          <Download className="h-4 w-4" />
          {t("act.download_stl")}{isZip ? ' (ZIP)' : ''}
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
          onClick={onDownloadScad}
          disabled={disabled}
          className="w-full gap-2"
          title={disabled ? "Render model first" : undefined}
        >
          <FileCode className="h-4 w-4" />
          {t("act.download_scad")}
        </Button>
      </AuthGate>

      <div className="text-xs text-muted-foreground mb-1">{t("act.export_img")}</div>
      <div className="grid grid-cols-2 gap-2">
        {cameraViews.map(view => (
          <Button key={view.id} variant="outline" size="sm" className="min-h-[44px]" onClick={() => onExportImage(view.id)} disabled={disabled} title={disabled ? "Render model first" : undefined}>
            {getLabel(view, 'label', language)}
          </Button>
        ))}
      </div>

      <Button
        variant="outline"
        size="sm"
        onClick={onExportAllViews}
        disabled={disabled}
        className="w-full min-h-[44px]"
        title={disabled ? "Render model first" : undefined}
      >
        {t("act.export_all")}
      </Button>

      {(manifest?.bom || manifest?.assembly_steps) && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            const slug = manifest.project?.slug
            if (slug) window.open(`${getApiBase()}/api/projects/${slug}/datasheet?lang=${language}`, '_blank')
          }}
          className="w-full min-h-[44px] gap-2"
        >
          <FileText className="h-4 w-4" />
          {t("datasheet.generate")}
        </Button>
      )}
    </div>
  )
}
