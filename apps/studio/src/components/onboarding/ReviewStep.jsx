import { AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function ReviewStep({ analysis, warnings, onBack, onNext, t }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="text-lg font-semibold">{t("onboard.review_title")}</div>

      {warnings.length > 0 && (
        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-md p-3">
          <div className="flex items-center gap-1 text-sm font-medium text-yellow-700 dark:text-yellow-400 mb-1">
            <AlertTriangle className="h-4 w-4" /> {t("onboard.warnings")}
          </div>
          <ul className="list-disc list-inside text-sm text-muted-foreground">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {Object.entries(analysis.files).map(([fname, data]) => (
        <div key={fname} className="border border-border rounded-md p-3">
          <div className="font-mono text-sm font-semibold mb-2">{fname}</div>
          <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
            <div>{t("onboard.variables")}: {data.variables.length}</div>
            <div>{t("onboard.modules")}: {data.modules.length}</div>
            <div>{t("onboard.includes")}: {data.includes.length}</div>
            <div>{t("onboard.render_modes")}: {data.render_modes.length > 0 ? data.render_modes.join(", ") : t("onboard.none")}</div>
          </div>
        </div>
      ))}

      <div className="flex gap-2">
        <Button variant="outline" onClick={onBack}>
          <ChevronLeft className="h-4 w-4 mr-1" /> {t("onboard.back")}
        </Button>
        <Button onClick={onNext}>
          {t("onboard.edit_manifest")} <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  )
}
