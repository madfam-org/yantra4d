import { useMemo, useState } from 'react'
import { Input } from '@/components/ui/input'
import { useLanguage } from '../../../contexts/system/LanguageProvider'
import { NODE_TYPES, nodeTypeNames } from '../../../lib/graph/graphDocument'

/** MIME type a palette drag carries, so the canvas ignores unrelated drops. */
export const PALETTE_DRAG_TYPE = 'application/x-yantra4d-graph-node'

interface PaletteGroup {
  key: string
  types: string[]
}

/**
 * Group the catalog for the palette from what each node IS, not from a list
 * kept here: anything that produces a non-solid (profiles) first, then solids
 * made from nothing, then operations that consume inputs. A node type the
 * engine adds tomorrow lands in the right group with no change to this file.
 */
export function paletteGroups(): PaletteGroup[] {
  const names = nodeTypeNames()
  const profiles = names.filter((n) => NODE_TYPES[n].output !== 'solid')
  const sources = names.filter((n) => NODE_TYPES[n].output === 'solid' && Object.keys(NODE_TYPES[n].inputs).length === 0)
  const operations = names.filter((n) => NODE_TYPES[n].output === 'solid' && Object.keys(NODE_TYPES[n].inputs).length > 0)
  return [
    { key: 'profiles', types: profiles },
    { key: 'solids', types: sources },
    { key: 'operations', types: operations },
  ].filter((g) => g.types.length > 0)
}

interface GraphPaletteProps {
  onAdd: (type: string) => void
}

export default function GraphPalette({ onAdd }: GraphPaletteProps) {
  const { t } = useLanguage()
  const [filter, setFilter] = useState('')
  const groups = useMemo(() => paletteGroups(), [])
  const needle = filter.trim().toLowerCase()

  return (
    <div className="border-b border-border px-2 py-1.5 text-xs" data-testid="graph-palette">
      <Input
        value={filter}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFilter(e.target.value)}
        placeholder={t('graph.palette_filter')}
        aria-label={t('graph.palette_filter')}
        className="h-7 text-xs mb-1.5"
      />
      <div className="max-h-28 overflow-y-auto space-y-1">
        {groups.map((group) => {
          const types = group.types.filter((n) => !needle || n.includes(needle))
          if (types.length === 0) return null
          return (
            <div key={group.key} role="group" aria-label={t(`graph.palette_${group.key}`)}>
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">
                {t(`graph.palette_${group.key}`)}
              </div>
              <div className="flex flex-wrap gap-1">
                {types.map((type) => (
                  <button
                    key={type}
                    type="button"
                    draggable
                    onDragStart={(e: React.DragEvent<HTMLButtonElement>) => {
                      e.dataTransfer.setData(PALETTE_DRAG_TYPE, type)
                      e.dataTransfer.effectAllowed = 'copy'
                    }}
                    onClick={() => onAdd(type)}
                    className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[11px] min-h-[32px] md:min-h-0 hover:bg-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    title={t('graph.palette_add', { type })}
                    data-testid={`graph-palette-${type}`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
