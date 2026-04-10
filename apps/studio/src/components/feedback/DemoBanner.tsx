import React, { useState } from 'react'
import { X } from 'lucide-react'
import { useAuth, isAuthEnabled } from '../../contexts/auth/AuthProvider'
import { useTier } from '../../hooks/system/useTier'
import { useLanguage } from '../../contexts/system/LanguageProvider'

export default function DemoBanner(): React.ReactNode {
  const [dismissed, setDismissed] = useState(false)
  const { isAuthenticated } = useAuth()
  const { tier } = useTier()
  const { t } = useLanguage()

  // Only show in demo mode for unauthenticated users
  if (!isAuthEnabled || isAuthenticated || dismissed) return null
  if (tier !== 'guest') return null

  return (
    <div className="relative bg-primary/10 border-b border-primary/20 px-4 py-2.5 text-sm text-center">
      <span className="text-foreground">
        {t('demo.welcome')}{' '}
        <a
          href="https://yantra4d.com/#pricing"
          className="font-medium text-primary underline underline-offset-2"
        >
          {t('demo.create_account')}
        </a>{' '}
        {t('demo.unlock_features')}
      </span>
      <button
        onClick={() => setDismissed(true)}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-sm hover:bg-primary/10"
        aria-label="Dismiss banner"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}
