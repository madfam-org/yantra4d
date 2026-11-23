/**
 * AnimationPanel.tsx — the cartridge's parameter sweeps, in the sidebar's
 * Design tab.
 *
 * A sweep is a path from one parameter setting to another (`animations[]` in
 * the manifest). Playing one renders its frames on the server and shows them
 * in the viewer, which is the `animation` feature: Pro and above
 * (apps/api/tiers.json). Every visitor sees which sweeps a cartridge declares;
 * a tier without playback gets the Studio's usual locked control, which opens
 * the upgrade prompt instead of a request that would be refused.
 *
 * The player state lives in ProjectProvider (`useSweepPlayer`), so this panel
 * can unmount — another tab, the phone sheet closing — without stopping it.
 */

import { AlertTriangle, Download, Film, Lock, Pause, Play, Square, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { sweepSeconds, type SweepDefinition } from '../../lib/sweeps'
import type { SweepPlayer } from '../../hooks/render/useSweepPlayer'

export interface AnimationPanelProps {
  sweeps: SweepDefinition[]
  player: SweepPlayer
  /** The visitor's tier includes playback (`animation` in tiers.json). */
  canPlay: boolean
  /** A locked sweep was chosen, or the server refused one: offer the upgrade. */
  onLocked: () => void
  /** The sweep's display label in the visitor's language. */
  labelOf: (sweep: SweepDefinition) => string
  /** The mode on screen; a sweep in another mode says which one it shows. */
  currentMode?: string | null
  modeLabelOf?: (modeId: string) => string
}

/** Small controls keep a 44 px target on touch screens (DESIGN.md, AGENTS.md). */
const TOUCH = 'h-auto min-h-[44px] md:h-8 md:min-h-0'

export default function AnimationPanel({
  sweeps, player, canPlay, onLocked, labelOf, currentMode, modeLabelOf,
}: AnimationPanelProps) {
  const { t } = useLanguage()
  if (sweeps.length === 0) return null

  const activeId = player.status === 'idle' ? null : player.sweep?.id ?? null
  const busy = player.status === 'rendering'

  const start = async (sweep: SweepDefinition) => {
    if (!canPlay) {
      onLocked()
      return
    }
    const result = await player.play(sweep)
    // A tier the server does not grant playback to (a stale session, a plan
    // that changed) is offered the upgrade, not shown an error.
    if (result === 'forbidden') onLocked()
  }

  return (
    <section aria-labelledby="sweeps-heading" className="space-y-2" data-testid="sweep-panel">
      <div>
        <h2
          id="sweeps-heading"
          className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground"
        >
          <Film className="h-3.5 w-3.5" aria-hidden="true" />
          {t('sweep.title')}
        </h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {canPlay ? t('sweep.subtitle') : t('sweep.subtitle_locked')}
        </p>
      </div>

      <ul className="space-y-2">
        {sweeps.map(sweep => {
          const label = labelOf(sweep) || sweep.id
          const active = sweep.id === activeId
          const otherMode = sweep.mode && currentMode && sweep.mode !== currentMode
            ? (modeLabelOf?.(sweep.mode) || sweep.mode)
            : null
          return (
            <li
              key={sweep.id}
              data-testid={`sweep-row-${sweep.id}`}
              className={`rounded-md border bg-card p-2 ${active ? 'border-primary/50' : 'border-border'}`}
            >
              <div className="flex items-start gap-2">
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium leading-tight [overflow-wrap:anywhere]">{label}</div>
                  <div className="mt-0.5 font-mono text-xs text-muted-foreground">
                    {t('sweep.meta', { frames: sweep.frames, seconds: sweepSeconds(sweep) })}
                  </div>
                  {otherMode && (
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {t('sweep.in_mode', { mode: otherMode })}
                    </div>
                  )}
                </div>

                {!active && (
                  canPlay ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className={`${TOUCH} shrink-0 gap-1.5 px-3 text-xs`}
                      onClick={() => start(sweep)}
                      disabled={busy}
                      aria-label={t('sweep.play_label', { label })}
                    >
                      <Play className="h-3.5 w-3.5" aria-hidden="true" />
                      {t('sweep.play')}
                    </Button>
                  ) : (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className={`${TOUCH} shrink-0 gap-1.5 px-3 text-xs text-muted-foreground`}
                      onClick={() => start(sweep)}
                      title={t('tier.pro_required')}
                      aria-label={t('sweep.locked_label', { label })}
                    >
                      <Lock className="h-3.5 w-3.5" aria-hidden="true" />
                      {t('tier.name_pro')}
                    </Button>
                  )
                )}

                {active && player.status === 'rendering' && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className={`${TOUCH} shrink-0 gap-1.5 px-3 text-xs`}
                    onClick={player.cancel}
                  >
                    <X className="h-3.5 w-3.5" aria-hidden="true" />
                    {t('btn.cancel')}
                  </Button>
                )}

                {active && (player.status === 'playing' || player.status === 'paused') && (
                  <div className="flex shrink-0 gap-1">
                    {player.frames.length > 1 && (
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="h-11 w-11 md:h-8 md:w-8"
                        onClick={player.status === 'playing' ? player.pause : player.resume}
                        aria-label={player.status === 'playing' ? t('sweep.pause') : t('sweep.resume')}
                        title={player.status === 'playing' ? t('sweep.pause') : t('sweep.resume')}
                        disabled={player.exporting}
                      >
                        {player.status === 'playing'
                          ? <Pause className="h-3.5 w-3.5" aria-hidden="true" />
                          : <Play className="h-3.5 w-3.5" aria-hidden="true" />}
                      </Button>
                    )}
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-11 w-11 md:h-8 md:w-8"
                      onClick={player.stop}
                      aria-label={t('sweep.stop')}
                      title={t('sweep.stop')}
                    >
                      <Square className="h-3.5 w-3.5" aria-hidden="true" />
                    </Button>
                  </div>
                )}

                {active && player.status === 'error' && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-11 w-11 shrink-0 md:h-8 md:w-8"
                    onClick={player.stop}
                    aria-label={t('sweep.dismiss')}
                    title={t('sweep.dismiss')}
                  >
                    <X className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                )}
              </div>

              {active && player.status === 'rendering' && (
                <div className="mt-2 flex items-center gap-2">
                  <div
                    role="progressbar"
                    aria-label={t('sweep.rendering_label', { label })}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={Math.round(player.progress)}
                    className="h-1.5 flex-1 overflow-hidden rounded-full bg-secondary"
                  >
                    <div className="h-full bg-primary transition-[width]" style={{ width: `${player.progress}%` }} />
                  </div>
                  <span className="shrink-0 font-mono text-xs text-muted-foreground">
                    {t('sweep.rendering', { progress: Math.round(player.progress) })}
                  </span>
                </div>
              )}

              {active && (player.status === 'playing' || player.status === 'paused') && (
                <div className="mt-2 space-y-2">
                  {player.frames.length > 1 && (
                    <div className="flex items-center gap-3">
                      <Slider
                        className="flex-1 py-3 md:py-1"
                        min={0}
                        max={player.frames.length - 1}
                        step={1}
                        value={[player.index]}
                        onValueChange={(v: number[]) => player.seek(v[0])}
                        aria-label={t('sweep.scrubber', { label })}
                        disabled={player.exporting}
                      />
                      <span className="shrink-0 font-mono text-xs text-muted-foreground">
                        {t('sweep.frame_of', { current: player.index + 1, total: player.frames.length })}
                      </span>
                    </div>
                  )}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className={`${TOUCH} w-full gap-1.5 text-xs`}
                    onClick={player.exportWebM}
                    disabled={player.exporting}
                  >
                    <Download className="h-3.5 w-3.5" aria-hidden="true" />
                    {player.exporting ? t('sweep.recording') : t('sweep.export_webm')}
                  </Button>
                </div>
              )}

              {active && player.error && (
                <p role="alert" className="mt-2 flex items-start gap-1.5 rounded-md bg-destructive/10 p-2 text-xs text-foreground">
                  <AlertTriangle className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  <span className="[overflow-wrap:anywhere]">
                    {player.error.code === 'no_canvas' ? t('sweep.error_no_canvas') : t('sweep.error_render')}
                    {player.error.detail && (
                      <span className="mt-0.5 block font-mono text-muted-foreground">{player.error.detail}</span>
                    )}
                  </span>
                </p>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
