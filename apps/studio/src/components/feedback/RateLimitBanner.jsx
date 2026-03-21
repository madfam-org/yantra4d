import { useRateLimit } from '../../services/core/apiClient'
import { useTier } from '../../hooks/system/useTier'
import { isAuthEnabled } from '../../contexts/auth/AuthProvider'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useManifest } from '../../contexts/project/ManifestProvider'
import { canRunWasm } from '../../services/engine/renderService'

export default function RateLimitBanner() {
  const { remaining, limit } = useRateLimit()
  const { canAccess } = useTier()
  const { t } = useLanguage()
  const { manifest } = useManifest()

  // Don't show if auth is off or no rate limit info yet
  if (!isAuthEnabled || remaining === null) return null

  const pct = limit > 0 ? remaining / limit : 1
  const isWarning = pct <= 0.3 && pct > 0
  const isExhausted = remaining <= 0
  const wasmAvailable = canRunWasm(manifest)

  if (!isWarning && !isExhausted) return null

  return (
    <div className={`px-4 py-2 text-sm text-center ${
      isExhausted
        ? 'bg-destructive/15 text-destructive'
        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200'
    }`}>
      {isExhausted ? (
        <>
          {t('ratelimit.server_exhausted').replace('{limit}', String(limit))}{' '}
          {wasmAvailable && (
            <span className="font-medium">{t('ratelimit.wasm_available')}</span>
          )}
          {!wasmAvailable && !canAccess('basic') ? (
            <>{' '}<a href="https://yantra4d.com/#pricing" className="underline font-medium">{t('demo.create_account')}</a></>
          ) : !wasmAvailable && !canAccess('pro') ? (
            <>{' '}<a href="https://yantra4d.com/#pricing" className="underline font-medium">Upgrade to Pro</a></>
          ) : null}
        </>
      ) : (
        <>
          {t('ratelimit.server_warning').replace('{remaining}', String(remaining))}{' '}
          {wasmAvailable && (
            <span>{t('ratelimit.wasm_suggestion')}</span>
          )}
          {!wasmAvailable && !canAccess('pro') && (
            <a href="https://yantra4d.com/#pricing" className="underline font-medium">Upgrade for more</a>
          )}
        </>
      )}
    </div>
  )
}
