import { Label } from "@/components/ui/label"
import { useLanguage } from "../../contexts/system/LanguageProvider"
import {
  QUALITY_MODES, setQualityMode, useQualityMode, useQualityReadings, type QualityMode,
} from '../../lib/viewerQuality'

const MODE_LABEL_KEYS: Record<QualityMode, string> = {
  auto: 'viewer.quality.auto',
  sharp: 'viewer.quality.sharp',
  balanced: 'viewer.quality.balanced',
  battery: 'viewer.quality.battery',
}

const ms = (value: number | null) => (value === null ? '—' : value.toFixed(1))

/** Render-quality mode plus the viewer's live benchmark readings (View panel). */
export default function ViewerQualityPanel() {
  const { t } = useLanguage()
  const mode = useQualityMode()
  const readings = useQualityReadings()

  return (
    <div
      className="space-y-2 border-t border-border pt-4"
      data-testid="viewer-quality"
      data-quality-mode={mode}
      data-render-scale={readings.scale}
      data-gpu-ms-p50={readings.gpuMsP50 ?? ''}
      data-gpu-ms-p90={readings.gpuMsP90 ?? ''}
    >
      <Label htmlFor="viewer-quality-mode" className="text-base font-semibold">{t('viewer.quality.title')}</Label>
      <select
        id="viewer-quality-mode"
        className="w-full px-3 py-2 text-base md:text-sm min-h-[44px] rounded-md border border-border bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        value={mode}
        onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setQualityMode(e.target.value as QualityMode)}
      >
        {QUALITY_MODES.map((m) => <option key={m} value={m}>{t(MODE_LABEL_KEYS[m])}</option>)}
      </select>
      <p className="text-xs text-muted-foreground">{t('viewer.quality.hint')}</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
        <dt className="text-muted-foreground">{t('viewer.quality.gpu')}</dt>
        <dd className="truncate font-mono" title={readings.gpu ?? undefined}>{readings.gpu ?? t('viewer.quality.unavailable')}</dd>
        <dt className="text-muted-foreground">{t('viewer.quality.browser')}</dt>
        <dd className="font-mono">{readings.browser || '—'}</dd>
        <dt className="text-muted-foreground">{t('viewer.quality.scale')}</dt>
        <dd className="font-mono">{Math.round(readings.scale * 100)}%</dd>
        <dt className="text-muted-foreground">{t('viewer.quality.gpu_time')}</dt>
        <dd className="font-mono">
          {readings.timerQuery ? `${ms(readings.gpuMsP50)} / ${ms(readings.gpuMsP90)} ms` : t('viewer.quality.unavailable')}
        </dd>
        <dt className="text-muted-foreground">{t('viewer.quality.fps')}</dt>
        <dd className="font-mono">{readings.fps > 0 ? readings.fps : t('viewer.quality.idle')}</dd>
        <dt className="text-muted-foreground">{t('viewer.quality.draws')}</dt>
        <dd className="font-mono">{readings.drawCalls} · {readings.triangles.toLocaleString()}</dd>
      </dl>
    </div>
  )
}
