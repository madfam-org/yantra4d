import React from 'react';
import {
    AlertDialog,
    AlertDialogContent,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogCancel,
} from '../ui/alert-dialog';
import { useLanguage } from '../../contexts/LanguageProvider';

export default function UpgradeDialog({ isOpen, onClose, feature }) {
    const { t } = useLanguage();

    return (
        <AlertDialog open={isOpen} onOpenChange={onClose}>
            <AlertDialogContent className="sm:max-w-md">
                <AlertDialogHeader>
                    <AlertDialogTitle className="flex items-center gap-2 text-xl">
                        <span>✨</span> {t("tier.upgrade_title") || "Unlock Limitless Creation"}
                    </AlertDialogTitle>
                    <AlertDialogDescription className="pt-2 text-base">
                        {t("tier.upgrade_desc_1") || "You've discovered a Pro feature!"}
                        <br />
                        <br />
                        {t("tier.upgrade_desc_2") || "Upgrade your plan to access:"} <strong className="text-foreground">{feature}</strong>.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter className="mt-6 flex-col space-y-2 sm:flex-row sm:space-x-2 sm:space-y-0">
                    <AlertDialogCancel onClick={onClose} className="w-full sm:w-auto">
                        {t("tier.maybe_later") || "Maybe Later"}
                    </AlertDialogCancel>
                    <a
                        href="https://4d.madfam.io/#pricing"
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={onClose}
                        className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 w-full sm:w-auto"
                    >
                        {t("tier.upgrade_button") || "Upgrade to Pro"}
                    </a>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
