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

export default function ConfirmRenderDialog({ open, onConfirm, onCancel, estimatedTime }) {
    const minutes = Math.ceil(estimatedTime / 60)
    const timeDisplay = estimatedTime >= 60
        ? `~${minutes} minute${minutes > 1 ? 's' : ''}`
        : `~${Math.round(estimatedTime)} seconds`

    return (
        <AlertDialog open={open} onOpenChange={(isOpen) => !isOpen && onCancel()}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>⚠️ Long Render Warning</AlertDialogTitle>
                    <AlertDialogDescription className="space-y-2">
                        <p>This render is estimated to take <strong>{timeDisplay}</strong>.</p>
                        <p className="text-sm text-muted-foreground">
                            The application may appear unresponsive during this time.
                        </p>
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel onClick={onCancel}>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={onConfirm}>Render Anyway</AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    )
}
