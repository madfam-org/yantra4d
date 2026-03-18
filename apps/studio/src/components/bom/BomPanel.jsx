import { useMemo } from 'react'
import { Parser } from 'expr-eval'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useManifest } from '../../contexts/project/ManifestProvider'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Copy, ExternalLink, Printer, Settings, Wrench } from 'lucide-react'
import { toast } from 'sonner'

const parser = new Parser()

function evaluateQuantity(formula, params) {
  if (typeof formula === 'number') return formula
  try {
    return parser.parse(formula).evaluate(params)
  } catch {
    return formula
  }
}

export default function BomPanel({ params, mode }) {
  const { language, t } = useLanguage()
  const { manifest, getLabel } = useManifest()

  const hardware = manifest?.bom?.hardware
  const activeMode = manifest?.modes?.find(m => m.id === mode)

  // Evaluate dynamic hardware quantities from manifest formulas
  const hardwareRows = useMemo(() => {
    if (!hardware) return []
    return hardware
      .map(item => ({
        ...item,
        quantity: evaluateQuantity(item.quantity_formula, params),
      }))
      .filter(item => item.quantity > 0)
  }, [hardware, params])

  // Get active printed parts based on the selected mode
  const printedRows = useMemo(() => {
    if (!activeMode || !activeMode.parts) return []
    const pqMap = activeMode.part_quantities || {}
    return activeMode.parts.map(partId => {
      const partDef = manifest.parts?.find(p => p.id === partId)
      const formula = pqMap[partId]
      return {
        id: partId,
        label: partDef?.label || activeMode.label,
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
    bomText += `Project: ${getLabel(manifest.project, 'name', language)}\n`
    bomText += `Mode: ${getLabel(activeMode, 'label', language)}\n\n`

    if (hasPrintedParts) {
      bomText += `## Printed Parts\n`
      printedRows.forEach(row => {
        bomText += `- ${row.quantity}x ${getLabel(row, 'label', language)} (${row.unit})\n`
      })
      bomText += `\n`
    }

    if (hasHardware) {
      bomText += `## External Hardware\n`
      hardwareRows.forEach(row => {
        bomText += `- ${row.quantity}x ${getLabel(row, 'label', language)} (${row.unit})\n`
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
                        {getLabel(row, 'label', language)}
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
                    <TableRow key={row.id}>
                      <TableCell className="py-2.5 font-medium text-xs">
                        {row.supplier_url ? (
                          <a href={row.supplier_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline inline-flex items-center gap-1 group">
                            {getLabel(row, 'label', language)}
                            <ExternalLink className="w-3 h-3 opacity-50 group-hover:opacity-100 transition-opacity" />
                          </a>
                        ) : (
                          getLabel(row, 'label', language)
                        )}
                      </TableCell>
                      <TableCell className="py-2.5 text-right font-mono text-xs">
                        {row.quantity}
                        <span className="text-muted-foreground ml-1 font-sans text-[10px]">{row.unit || 'pcs'}</span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
