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
import { useLanguage } from '../../contexts/system/LanguageProvider';
import { useAuth } from '../../contexts/auth/AuthProvider';
import { getCheckoutUrl } from '../../lib/billing';

interface UpgradeDialogProps {
    isOpen: boolean
    onClose: (open: boolean) => void
    feature: string
}

/**
 * The upgrade prompt shown when a user hits a pro-gated feature.
 *
 * The primary CTA goes straight to Dhanam checkout (lib/billing.ts) with the
 * user id and a return URL, so the purchase lands back where the user was.
 * Before this, the CTA linked to yantra4d.com/#pricing — an anchor that did
 * not exist — and the only component that called the checkout builder
 * (UpgradeModal) was never mounted anywhere.
 */
export default function UpgradeDialog({ isOpen, onClose, feature }: UpgradeDialogProps) {
    const { t } = useLanguage();
    const { user } = useAuth();

    const returnUrl = typeof window !== 'undefined' ? window.location.href : undefined;
    const checkoutUrl = getCheckoutUrl('pro', user?.id, returnUrl);

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

                <div className="mt-2 rounded-md border border-border p-3">
                    <div className="flex items-baseline justify-between">
                        <span className="font-medium">{t("tier.pro_plan_name") || "Yantra4D Pro"}</span>
                        <span className="text-sm text-muted-foreground">{t("tier.pro_price") || "from $9/mo"}</span>
                    </div>
                    <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                        <li>{t("tier.perk_renders") || "More server renders, all export formats"}</li>
                        <li>{t("tier.perk_cadquery") || "CadQuery engine & STEP export"}</li>
                        <li>{t("tier.perk_github") || "GitHub import & code editor"}</li>
                        <li>{t("tier.perk_print") || "Print dispatch & manufacturing quotes"}</li>
                    </ul>
                </div>

                <AlertDialogFooter className="mt-6 flex-col space-y-2 sm:flex-row sm:space-x-2 sm:space-y-0">
                    <AlertDialogCancel onClick={onClose} className="w-full sm:w-auto">
                        {t("tier.maybe_later") || "Maybe Later"}
                    </AlertDialogCancel>
                    <a
                        href="https://yantra4d.com/#pricing"
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={onClose}
                        className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 border border-border bg-background hover:bg-muted h-10 px-4 py-2 w-full sm:w-auto"
                    >
                        {t("tier.see_plans") || "See plans"}
                    </a>
                    <a
                        href={checkoutUrl}
                        data-testid="upgrade-checkout-link"
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
