import { Button } from "@/components/ui/button"
import { Download } from 'lucide-react'
import { useLanguage } from "../contexts/LanguageProvider"
import { useManifest } from "../contexts/ManifestProvider"

export default function ExportPanel({ parts, mode, manifest, onDownloadStl, onExportImage, onExportAllViews }) {
  const { language, t } = useLanguage()
  const { getCameraViews, getLabel } = useManifest()
  const cameraViews = getCameraViews()
  const disabled = parts.length === 0

  // Derive expected part count from manifest so label is correct before first render
  const modeConfig = manifest?.modes?.find(m => m.id === mode)
  const expectedPartCount = modeConfig?.parts?.length || 0
  const isZip = expectedPartCount > 1

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-4">
      <Button
        variant="outline"
        onClick={onDownloadStl}
        disabled={disabled}
        className="w-full gap-2"
        title={t("tooltip.download")}
      >
        <Download className="h-4 w-4" />
        {t("act.download_stl")}{isZip ? ' (ZIP)' : ''}
      </Button>

      <div className="text-xs text-muted-foreground mb-1">{t("act.export_img")}</div>
      <div className="grid grid-cols-2 gap-2">
        {cameraViews.map(view => (
          <Button key={view.id} variant="outline" size="sm" className="min-h-[44px]" onClick={() => onExportImage(view.id)} disabled={disabled}>
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
      >
        {t("act.export_all")}
      </Button>
    </div>
  )
}
