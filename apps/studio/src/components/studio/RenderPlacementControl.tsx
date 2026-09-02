import { useCallback, useEffect, useMemo, useState } from 'react'
import { Cpu, Server } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useProject } from '../../contexts/project/ProjectProvider'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useRateLimit, isUnlimited } from '../../services/core/apiClient'
import { previewPlacement, ensureCapabilityProbe } from '../../services/engine/renderService'
import {
  getPlacementPreference,
  setPlacementPreference,
  subscribePlacementPreference,
  type PlacementPreference,
} from '../../services/engine/renderCapability'

/**
 * Where this render will run, and the visitor's say in it.
 *
 * TWO RULES THIS COMPONENT EXISTS TO ENFORCE:
 *
 *  1. A BROWSER render never shows a quota. It does not consume one. Putting
 *     "12 left" next to a free render teaches the visitor that everything they
 *     do here is metered, which is the opposite of the truth and the opposite
 *     of what we want them to feel when they drag a slider.
 *  2. A SERVER render says what it costs, in the same breath as saying where
 *     it runs — so the trade the Auto/Browser/Server control offers is legible
 *     at the moment they are looking at it.
 */
export default function RenderPlacementControl() {
  const { manifest, mode, params, projectSlug, exportFormat } = useProject()
  const { t } = useLanguage()
  const { remaining, limit } = useRateLimit()
  const [preference, setPreference] = useState<PlacementPreference>(() => getPlacementPreference())

  // The measured half of the capability probe. Fire-and-forget: the badge
  // renders immediately from static signals and re-renders if the measurement
  // moves the tier.
  const [probeGeneration, setProbeGeneration] = useState(0)
  useEffect(() => {
    let cancelled = false
    ensureCapabilityProbe().then(() => {
      if (!cancelled) setProbeGeneration(g => g + 1)
    })
    return () => { cancelled = true }
  }, [])

  useEffect(() => subscribePlacementPreference(setPreference), [])

  // `exportFormat` belongs here because it can DECIDE the placement: the browser
  // kernel only ever emits STL, so picking `step` in the export panel moves the
  // next render to the server (rule 4) and this badge has to say so.
  const decision = useMemo(
    () => previewPlacement(manifest, mode, params, projectSlug, exportFormat),
    // `probeGeneration` is a deliberate dependency: the probe changes the tier,
    // which can change the decision, and nothing else would tell us.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [manifest, mode, params, projectSlug, exportFormat, preference, probeGeneration],
  )

  const onPreferenceChange = useCallback((value: string) => {
    setPlacementPreference(value as PlacementPreference)
  }, [])

  const isBrowser = decision.placement === 'browser'

  // The quota, only ever alongside a server placement.
  const unlimited = isUnlimited(limit)
  const quotaLabel = unlimited
    ? t('tier.unlimited')
    : remaining !== null ? String(remaining) : null

  const badgeText = isBrowser
    ? t('placement.badge.browser')
    : quotaLabel !== null
      ? t('placement.badge.server_with_quota').replace('{remaining}', quotaLabel)
      : t('placement.badge.server')

  // One line saying why. Reason keys are stable and machine-readable
  // (`estimate_over_threshold:62s>45s`); the key before the colon is what maps
  // to a sentence, and an unmapped key degrades to nothing rather than to
  // developer jargon in the UI.
  const primaryReason = decision.reasons[0] ?? ''
  const reasonKey = `placement.reason.${primaryReason.split(':')[0]}`
  const reasonText = t(reasonKey)
  const reason = reasonText === reasonKey ? '' : reasonText

  return (
    <div
      className="rounded-md border border-border bg-muted/40 px-2.5 py-2 text-xs"
      data-testid="render-placement"
      data-placement={decision.placement}
    >
      <div className="flex items-center gap-2">
        {isBrowser
          ? <Cpu className="h-3.5 w-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
          : <Server className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />}
        <span className="flex-1 truncate font-medium" data-testid="render-placement-badge">
          {badgeText}
        </span>
        <Select value={preference} onValueChange={onPreferenceChange} disabled={decision.hard}>
          <SelectTrigger
            className="h-7 w-[92px] shrink-0 text-xs"
            aria-label={t('placement.control.label')}
            data-testid="render-placement-select"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">{t('placement.option.auto')}</SelectItem>
            <SelectItem value="browser">{t('placement.option.browser')}</SelectItem>
            <SelectItem value="server">{t('placement.option.server')}</SelectItem>
          </SelectContent>
        </Select>
      </div>
      {reason && (
        <p className="mt-1 text-[11px] leading-tight text-muted-foreground" data-testid="render-placement-reason">
          {reason}
        </p>
      )}
    </div>
  )
}
