import { getCheckoutUrl, type Yantra4DTier } from '../../lib/billing';

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  feature: string;
  currentTier: Yantra4DTier;
  userId?: string;
}

/**
 * Modal shown when a user attempts a pro-gated feature.
 * Links to Dhanam checkout for Yantra4D Pro upgrade.
 */
export function UpgradeModal({ isOpen, onClose, feature, currentTier, userId }: UpgradeModalProps) {
  if (!isOpen) return null;

  const returnUrl = typeof window !== 'undefined' ? window.location.href : undefined;
  const checkoutUrl = getCheckoutUrl('pro', userId, returnUrl);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="relative w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-zinc-900"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="absolute right-3 top-3 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
          onClick={onClose}
          aria-label="Close"
        >
          &times;
        </button>

        <h2 className="text-lg font-semibold">Upgrade to Pro</h2>

        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          <strong>{feature}</strong> requires Yantra4D Pro.
          Unlock CadQuery, GitHub integration, AI code editor, premium exports, and more.
        </p>

        <div className="mt-4 rounded-md border border-zinc-200 p-3 dark:border-zinc-700">
          <div className="flex items-baseline justify-between">
            <span className="font-medium">Yantra4D Pro</span>
            <span className="text-sm text-zinc-500">from $9/mo</span>
          </div>
          <ul className="mt-2 space-y-1 text-xs text-zinc-500 dark:text-zinc-400">
            <li>Unlimited projects & renders</li>
            <li>CadQuery engine & STEP export</li>
            <li>GitHub import/editor</li>
            <li>AI code editor</li>
            <li>Print dispatch</li>
          </ul>
        </div>

        <div className="mt-4 flex gap-2">
          <a
            href={checkoutUrl}
            className="flex-1 rounded-md bg-indigo-600 px-4 py-2 text-center text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
          >
            Upgrade Now
          </a>
          <button
            onClick={onClose}
            className="rounded-md border border-zinc-200 px-4 py-2 text-sm text-zinc-600 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800"
          >
            Maybe Later
          </button>
        </div>

        <p className="mt-3 text-center text-xs text-zinc-400">
          Current tier: {currentTier}
        </p>
      </div>
    </div>
  );
}
