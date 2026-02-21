import { useMemo } from 'react'
import { Parser } from 'expr-eval'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useManifest } from '../../contexts/project/ManifestProvider'

const parser = new Parser()

function evaluateQuantity(formula, params) {
  if (typeof formula === 'number') return formula
  try {
    return parser.parse(formula).evaluate(params)
  } catch {
    return formula
  }
}

export default function BomPanel({ params }) {
  const { language, t } = useLanguage()
  const { manifest, getLabel } = useManifest()
  const hardware = manifest?.bom?.hardware

  const rows = useMemo(() => {
    if (!hardware) return []
    return hardware.map(item => ({
      ...item,
      quantity: evaluateQuantity(item.quantity_formula, params),
    }))
  }, [hardware, params])

  if (!hardware || hardware.length === 0) return null

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-4">
      <h2 className="text-sm font-semibold">{t('bom.title')}</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-left text-muted-foreground">
              <th className="py-1 pr-2">{t('bom.item')}</th>
              <th className="py-1 pr-2 text-right">{t('bom.qty')}</th>
              <th className="py-1">{t('bom.unit')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(row => (
              <tr key={row.id} className="border-b border-border/50">
                <td className="py-1.5 pr-2">
                  {row.supplier_url ? (
                    <a href={row.supplier_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                      {getLabel(row, 'label', language)}
                    </a>
                  ) : (
                    getLabel(row, 'label', language)
                  )}
                </td>
                <td className="py-1.5 pr-2 text-right font-mono">{row.quantity}</td>
                <td className="py-1.5 text-muted-foreground">{row.unit || 'pcs'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
