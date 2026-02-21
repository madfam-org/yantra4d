import { useRateLimit } from '../../services/core/apiClient'
import { useTier } from '../../hooks/useTier'
import { isAuthEnabled } from '../../contexts/AuthProvider'

export default function RateLimitBanner() {
  const { remaining, limit, tier } = useRateLimit()
  const { canAccess } = useTier()

  // Don't show if auth is off or no rate limit info yet
  if (!isAuthEnabled || remaining === null) return null

  const pct = limit > 0 ? remaining / limit : 1
  const isWarning = pct <= 0.3 && pct > 0
  const isExhausted = remaining <= 0

  if (!isWarning && !isExhausted) return null

  return (
    <div className={`px-4 py-2 text-sm text-center ${
      isExhausted
        ? 'bg-destructive/15 text-destructive'
        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200'
    }`}>
      {isExhausted ? (
        <>
          Render limit reached ({limit}/hr for {tier} tier).{' '}
          {!canAccess('basic') ? (
            <a href="https://4d.madfam.io/#pricing" className="underline font-medium">Sign up for more</a>
          ) : !canAccess('pro') ? (
            <a href="https://4d.madfam.io/#pricing" className="underline font-medium">Upgrade to Pro</a>
          ) : null}
        </>
      ) : (
        <>
          {remaining} render{remaining !== 1 ? 's' : ''} remaining this hour.{' '}
          {!canAccess('pro') && (
            <a href="https://4d.madfam.io/#pricing" className="underline font-medium">Upgrade for more</a>
          )}
        </>
      )}
    </div>
  )
}
