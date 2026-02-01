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
import { useLanguage } from "../contexts/LanguageProvider"

export default function ConfirmRenderDialog({ open, onConfirm, onCancel, estimatedTime }) {
    const { t } = useLanguage()
    const minutes = Math.ceil(estimatedTime / 60)
    const timeDisplay = estimatedTime >= 60
        ? `~${minutes} minute${minutes > 1 ? 's' : ''}`
        : `~${Math.round(estimatedTime)} seconds`

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
