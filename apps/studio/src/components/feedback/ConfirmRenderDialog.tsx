import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { useLanguage } from "../../contexts/system/LanguageProvider"

interface ConfirmRenderDialogProps {
    open: boolean
    onConfirm: () => void
    onCancel: () => void
    estimatedTime: number
}

export default function ConfirmRenderDialog({ open, onConfirm, onCancel, estimatedTime }: ConfirmRenderDialogProps) {
    const { t } = useLanguage()
    const minutes = Math.ceil(estimatedTime / 60)
    // Localized: the English unit inside a translated sentence read
    // «tardará ~2 minutes» on the Spanish Studio.
    const timeDisplay = estimatedTime >= 60
        ? (minutes > 1
            ? t("dialog.render_time_minutes", { count: minutes })
            : t("dialog.render_time_one_minute"))
        : t("dialog.render_time_seconds", { count: Math.round(estimatedTime) })

    return (
        <AlertDialog open={open}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>{t("dialog.render_warning_title")}</AlertDialogTitle>
                    <AlertDialogDescription asChild>
                        <div className="space-y-2">
                            <span className="block">{t("dialog.render_warning_body")} <strong>{timeDisplay}</strong>.</span>
                            <span className="block text-sm text-muted-foreground">
                                {t("dialog.render_warning_note")}
                            </span>
                        </div>
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel onClick={onCancel}>{t("btn.cancel")}</AlertDialogCancel>
                    <AlertDialogAction onClick={onConfirm}>{t("dialog.render_anyway")}</AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    )
}
