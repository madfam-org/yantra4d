import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Box, Workflow } from 'lucide-react'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Toggle } from '@/components/ui/toggle'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useModeGraph } from '../../hooks/project/useModeGraph'
import { bindingsFromManifest } from '../../lib/graph/graphBindings'
import type { ManifestParameterLike } from '../../lib/graph/graphExpressions'
import InsidePanel from './InsidePanel'

/** Desktop: whether Inside is open beside the 3D view, remembered per browser. */
const OPEN_KEY = 'yantra4d-inside-open'
/** How long a changed slider keeps its nodes marked after the last change. */
export const CHANGE_HIGHLIGHT_MS = 1800

function readOpen(): boolean {
  try { return localStorage.getItem(OPEN_KEY) === '1' } catch { return false }
}
function writeOpen(open: boolean): void {
  try { localStorage.setItem(OPEN_KEY, open ? '1' : '0') } catch { /* storage unavailable: not remembered */ }
}

/**
 * The parameter whose value changed most recently, for CHANGE_HIGHLIGHT_MS.
 * Scrubbing a slider keeps it set; a preset that changes many values marks none.
 */
function useRecentlyChangedParam(values: Record<string, unknown>): string | null {
  const previous = useRef(values)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [changed, setChanged] = useState<string | null>(null)
  useEffect(() => {
    const before = previous.current
    previous.current = values
    if (before === values) return
    const keys = Object.keys(values).filter((k) => !Object.is(before[k], values[k]))
    if (keys.length !== 1) return
    setChanged(keys[0])
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setChanged(null), CHANGE_HIGHLIGHT_MS)
  }, [values])
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])
  return changed
}

export interface GraphViewFrameProps {
  /** The 3D viewer; it stays mounted whichever view is showing, and across modes. */
  children: ReactNode
  /**
   * Whether the active mode declares a graph. When false the frame renders
   * only the viewer, in the same place, so switching between a script mode and
   * a graph mode never remounts the viewer (and its WebGL context).
   */
  available: boolean
  slug: string
  mode: string
  isDesktop: boolean
  parameters: ManifestParameterLike[]
  values: Record<string, unknown>
  hoveredParamId: string | null
  labelOf: (parameterId: string) => string
}

const RAIL = 'h-9 rounded-md bg-muted p-1'
const RAIL_ITEM = 'h-7 min-w-[64px] rounded-sm px-3 text-xs font-medium text-muted-foreground hover:bg-transparent hover:text-foreground data-[state=on]:bg-background data-[state=on]:text-foreground data-[state=on]:shadow-sm'

/**
 * Wraps the 3D view of a mode that declares a graph with the "Inside" view of
 * that graph: side by side on desktop (the viewport keeps the larger share), a
 * 3D | Inside switch on smaller screens. Read-only and open to every visitor.
 */
export default function GraphViewFrame({ children, available, slug, mode, isDesktop, parameters, values, hoveredParamId, labelOf }: GraphViewFrameProps) {
  const { t } = useLanguage()
  const [desktopOpen, setDesktopOpen] = useState(readOpen)
  const [compactView, setCompactView] = useState<'3d' | 'inside'>('3d')
  const open = available && (isDesktop ? desktopOpen : compactView === 'inside')

  const graph = useModeGraph(slug, mode, open)
  const bindings = useMemo(() => bindingsFromManifest(parameters), [parameters])
  const recent = useRecentlyChangedParam(values)
  const activeParamId = hoveredParamId ?? recent

  const toggleDesktop = (next: boolean) => {
    setDesktopOpen(next)
    writeOpen(next)
  }

  return (
    <div className="flex h-full min-h-0 flex-col" data-testid="graph-view-frame" data-graph-available={available ? 'true' : 'false'} data-inside-open={open ? 'true' : 'false'}>
      {available && (<div className="flex h-11 shrink-0 items-center gap-2 border-b border-border bg-background px-2" role="toolbar" aria-label={t('inside.toolbar')}>
        {isDesktop ? (
          <Toggle
            pressed={desktopOpen}
            onPressedChange={toggleDesktop}
            size="sm"
            variant="outline"
            className="h-9 gap-1.5 px-3 text-xs data-[state=on]:border-primary"
            data-testid="inside-toggle"
          >
            <Workflow aria-hidden="true" className="!size-3.5" />
            {t('inside.toggle')}
          </Toggle>
        ) : (
          <ToggleGroup
            type="single"
            value={compactView}
            onValueChange={(v: string) => { if (v === '3d' || v === 'inside') setCompactView(v) }}
            className={RAIL}
            aria-label={t('inside.view_switch')}
            data-testid="inside-switch"
          >
            <ToggleGroupItem value="3d" className={RAIL_ITEM}>
              <Box aria-hidden="true" className="!size-3.5" /> {t('inside.view_3d')}
            </ToggleGroupItem>
            <ToggleGroupItem value="inside" className={RAIL_ITEM}>
              <Workflow aria-hidden="true" className="!size-3.5" /> {t('inside.toggle')}
            </ToggleGroupItem>
          </ToggleGroup>
        )}
        <span className="min-w-0 truncate text-xs text-muted-foreground">{t('inside.toolbar_hint')}</span>
      </div>)}

      <div className="flex min-h-0 flex-1">
        {/* The viewer is hidden, never unmounted, on a phone showing Inside: its scene and camera survive the switch. */}
        <div className={!isDesktop && open ? 'hidden' : 'relative min-w-0 flex-1'} data-testid="graph-view-3d">
          {children}
        </div>
        {open && (
          <div
            className={isDesktop ? 'min-w-[320px] max-w-[720px] basis-[45%] border-l border-border' : 'min-w-0 flex-1'}
            data-testid="graph-view-inside"
          >
            <InsidePanel
              key={`${slug}:${mode}`}
              state={graph}
              onRetry={graph.retry}
              bindings={bindings}
              values={values}
              labelOf={labelOf}
              activeParamId={activeParamId}
            />
          </div>
        )}
      </div>
    </div>
  )
}
