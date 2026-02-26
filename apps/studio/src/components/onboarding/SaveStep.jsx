import { Check, ChevronLeft } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function SaveStep({ saveSummary, onBack, onSave, onCancel, loading, t }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="text-lg font-semibold">{t("onboard.save_title")}</div>
      <div className="text-sm text-muted-foreground">
        {saveSummary}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" className="min-h-[44px]" onClick={onBack}>
          <ChevronLeft className="h-4 w-4 mr-1" /> {t("onboard.back")}
        </Button>
        <Button className="min-h-[44px]" onClick={onSave} disabled={loading}>
          {loading ? t("onboard.saving") : t("onboard.create_btn")}
          <Check className="h-4 w-4 ml-1" />
        </Button>
        {onCancel && (
          <Button variant="ghost" className="min-h-[44px]" onClick={onCancel}>
            {t("onboard.cancel")}
          </Button>
        )}
      </div>
    </div>
  )
}
