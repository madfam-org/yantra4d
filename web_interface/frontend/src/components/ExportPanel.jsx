import { Button } from "@/components/ui/button"
import { Download } from 'lucide-react'
import { useLanguage } from "../contexts/LanguageProvider"

export default function ExportPanel({ parts, mode, manifest, onDownloadStl, onExportImage, onExportAllViews }) {
  const { t } = useLanguage()
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
        <Button variant="outline" size="sm" onClick={() => onExportImage('iso')} disabled={disabled}>
          {t("view.iso")}
        </Button>
        <Button variant="outline" size="sm" onClick={() => onExportImage('top')} disabled={disabled}>
          {t("view.top")}
        </Button>
        <Button variant="outline" size="sm" onClick={() => onExportImage('front')} disabled={disabled}>
          {t("view.front")}
        </Button>
        <Button variant="outline" size="sm" onClick={() => onExportImage('right')} disabled={disabled}>
          {t("view.right")}
        </Button>
      </div>

      <Button
        variant="outline"
        size="sm"
        onClick={onExportAllViews}
        disabled={disabled}
        className="w-full"
      >
        {t("act.export_all")}
      </Button>
    </div>
  )
}
