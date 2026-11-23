/**
 * SweepStatusChip — says, over the viewer, that a sweep is on screen instead
 * of the visitor's configuration, and keeps pause and stop within reach when
 * the sidebar is not (a phone with the controls sheet closed).
 */
import { AlertTriangle, Film, Pause, Play, Square, X } from 'lucide-react'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import type { SweepPlayer } from '../../hooks/render/useSweepPlayer'

interface SweepStatusChipProps {
  player: SweepPlayer
  label: string
}

const ICON_BUTTON = 'inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 md:h-7 md:w-7'

export default function SweepStatusChip({ player, label }: SweepStatusChipProps) {
  const { t } = useLanguage()
  if (player.status === 'idle') return null

  const showing = player.status === 'playing' || player.status === 'paused'
  const announcement = player.status === 'rendering'
    ? t('sweep.rendering_label', { label })
    : player.status === 'playing'
      ? t('sweep.announce_playing', { label })
      : player.status === 'paused'
        ? t('sweep.announce_paused', { label })
        : t('sweep.error_render')

  return (
    <div
      data-testid="sweep-status-chip"
      role="group"
      aria-label={t('sweep.feature_name')}
      // Phones: a full-width row under the viewer's top controls, which fill
      // the top edge at 390 px. Wider: centred on the top edge, where the
      // prerendered-preview badge sits (hidden while a sweep is active).
      className="absolute left-2 right-2 top-14 z-20 flex items-center gap-1 rounded-lg border border-border bg-card/95 py-0.5 pl-2.5 pr-0.5 text-xs sm:left-1/2 sm:right-auto sm:top-2 sm:max-w-[calc(100%-2rem)] sm:-translate-x-1/2"
    >
      <span className="sr-only" role="status">{announcement}</span>
      {player.status === 'error'
        ? <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        : <Film className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />}
      <span className="min-w-0 truncate font-medium" aria-hidden="true">
        {player.status === 'error' ? t('sweep.error_render') : label}
      </span>

      {player.status === 'rendering' && (
        <>
          <span className="shrink-0 font-mono text-muted-foreground" aria-hidden="true">
            {t('sweep.rendering', { progress: Math.round(player.progress) })}
          </span>
          <button type="button" className={ICON_BUTTON} onClick={player.cancel} aria-label={t('btn.cancel')} title={t('btn.cancel')}>
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </>
      )}

      {showing && (
        <>
          <span className="shrink-0 font-mono text-muted-foreground" aria-hidden="true">
            {t('sweep.frame_short', { current: player.index + 1, total: player.frames.length })}
          </span>
          {player.frames.length > 1 && (
            <button
              type="button"
              className={ICON_BUTTON}
              onClick={player.status === 'playing' ? player.pause : player.resume}
              disabled={player.exporting}
              aria-label={player.status === 'playing' ? t('sweep.pause') : t('sweep.resume')}
              title={player.status === 'playing' ? t('sweep.pause') : t('sweep.resume')}
            >
              {player.status === 'playing'
                ? <Pause className="h-3.5 w-3.5" aria-hidden="true" />
                : <Play className="h-3.5 w-3.5" aria-hidden="true" />}
            </button>
          )}
          <button type="button" className={ICON_BUTTON} onClick={player.stop} aria-label={t('sweep.stop')} title={t('sweep.stop')}>
            <Square className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </>
      )}

      {player.status === 'error' && (
        <button type="button" className={ICON_BUTTON} onClick={player.stop} aria-label={t('sweep.dismiss')} title={t('sweep.dismiss')}>
          <X className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
