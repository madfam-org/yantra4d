import { useMemo } from 'react'
import { evaluateSafeFormula } from '../../lib/safeFormula'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useManifest } from '../../contexts/project/ManifestProvider'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Copy, ExternalLink, Printer, Settings, Wrench } from 'lucide-react'
import { toast } from 'sonner'

function evaluateQuantity(formula: string | number, params: Record<string, unknown>): number | string {
  if (typeof formula === 'number') return formula
  try {
    const result = evaluateSafeFormula(formula, params)
    return typeof result === 'number' ? result : Number(result)
  } catch {
    return formula
  }
}

interface BomPanelProps {
  params: Record<string, unknown>
  mode: string
}

export default function BomPanel({ params, mode }: BomPanelProps) {
  const { language, t } = useLanguage()
  const { manifest, getLabel } = useManifest()

  const hardware = (manifest as Record<string, unknown>)?.bom ? ((manifest as Record<string, unknown>).bom as Record<string, unknown>).hardware as Array<Record<string, unknown>> | undefined : undefined
  const activeMode = manifest?.modes?.find((m: Record<string, unknown>) => m.id === mode)

  // Evaluate dynamic hardware quantities from manifest formulas
  const hardwareRows = useMemo(() => {
    if (!hardware) return []
    return hardware
      .map(item => ({
        ...item,
        quantity: evaluateQuantity(item.quantity_formula as string | number, params),
      }))
      .filter(item => (item.quantity as number) > 0)
  }, [hardware, params])

  // Get active printed parts based on the selected mode
  const printedRows = useMemo(() => {
    if (!activeMode || !activeMode.parts) return []
    const pqMap = (activeMode as Record<string, unknown>).part_quantities as Record<string, string | number> || {}
    return (activeMode.parts as string[]).map(partId => {
      const partDef = manifest.parts?.find((p: Record<string, unknown>) => p.id === partId)
      const formula = pqMap[partId]
      return {
        id: partId,
        label: partDef?.label || (activeMode as Record<string, unknown>).label,
        quantity: formula != null ? evaluateQuantity(formula, params) : 1,
        unit: 'pcs',
        isPrinted: true
      }
    })
  }, [activeMode, manifest.parts, params])

  const hasHardware = hardwareRows.length > 0
  const hasPrintedParts = printedRows.length > 0

  if (!hasHardware && !hasPrintedParts) return null

  const handleCopyBom = () => {
    let bomText = `# Bill of Materials\n`
    bomText += `Project: ${getLabel(manifest.project as never, 'name', language)}\n`
    bomText += `Mode: ${getLabel(activeMode as never, 'label', language)}\n\n`

    if (hasPrintedParts) {
      bomText += `## Printed Parts\n`
      printedRows.forEach(row => {
        bomText += `- ${row.quantity}x ${getLabel(row as never, 'label', language)} (${row.unit})\n`
      })
      bomText += `\n`
    }

    if (hasHardware) {
      bomText += `## External Hardware\n`
      hardwareRows.forEach(row => {
        bomText += `- ${row.quantity}x ${getLabel(row as never, 'label', language)} (${row.unit})\n`
      })
    }

    navigator.clipboard.writeText(bomText).then(() => {
      toast.success(t('toast.copied_bom') || 'BOM copied to clipboard!')
    }).catch(err => {
      console.error('Failed to copy BOM: ', err)
      toast.error('Failed to copy. Please try again.')
    })
  }

  return (
    <div className="flex flex-col gap-4 border-t border-border pt-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Settings className="w-4 h-4 text-muted-foreground" />
          {t('bom.title')}
        </h2>
        <Button variant="outline" size="sm" onClick={handleCopyBom} className="h-8 gap-1.5 text-xs" title="Copy text to clipboard">
          <Copy className="h-3 w-3" />
          <span className="sr-only sm:not-sr-only">Copy</span>
        </Button>
      </div>

      <div className="space-y-6">
        {/* Printed Parts Section */}
        {hasPrintedParts && (
          <div className="space-y-2">
            <h3 className="text-xs font-medium text-muted-foreground flex items-center gap-2">
              <Printer className="w-3.5 h-3.5" />
              Printed Parts
            </h3>
            <div className="rounded-md border border-border/60 overflow-hidden bg-muted/20">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="py-2 h-9">Item</TableHead>
                    <TableHead className="py-2 h-9 text-right w-12">Qty</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {printedRows.map(row => (
                    <TableRow key={row.id}>
                      <TableCell className="py-2.5 font-medium text-xs flex items-center gap-2">
                        {getLabel(row as never, 'label', language)}
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 border-transparent bg-primary/10 text-primary uppercase">
                          3D Print
                        </Badge>
                      </TableCell>
                      <TableCell className="py-2.5 text-right font-mono text-xs">{row.quantity}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        {/* External Hardware Section */}
        {hasHardware && (
          <div className="space-y-2">
            <h3 className="text-xs font-medium text-muted-foreground flex items-center gap-2">
              <Wrench className="w-3.5 h-3.5" />
              External Hardware
            </h3>
            <div className="rounded-md border border-border/60 overflow-hidden bg-muted/20">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="py-2 h-9">Item</TableHead>
                    <TableHead className="py-2 h-9 text-right w-12">Qty</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {hardwareRows.map(row => (
                    <TableRow key={row.id as string}>
                      <TableCell className="py-2.5 font-medium text-xs">
                        {row.supplier_url ? (
                          <a href={row.supplier_url as string} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline inline-flex items-center gap-1 group">
                            {getLabel(row as never, 'label', language)}
                            <ExternalLink className="w-3 h-3 opacity-50 group-hover:opacity-100 transition-opacity" />
                          </a>
                        ) : (
                          getLabel(row as never, 'label', language)
                        )}
                      </TableCell>
                      <TableCell className="py-2.5 text-right font-mono text-xs">
                        {row.quantity as React.ReactNode}
                        <span className="text-muted-foreground ml-1 font-sans text-[10px]">{(row.unit as string) || 'pcs'}</span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </div>

      {/* ForgeSight pricing integration (coming soon) */}
      <div className="pt-2 border-t border-border">
        <Button
          variant="outline"
          size="sm"
          disabled
          className="w-full h-9 gap-2 text-xs opacity-60"
          title="Coming soon — requires ForgeSight integration"
        >
          <Printer className="h-3 w-3" />
          Get Quote
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">Soon</Badge>
        </Button>
      </div>
    </div>
  )
}
