import React, { useState, useMemo, useEffect } from 'react'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useManifest } from '../../contexts/project/ManifestProvider'
import { estimatePrint, getMaterialProfiles, buildMaterialLookup, getInfillPatterns, getNozzleDiameters, fetchMaterialPricing, computeCostRange } from '../../lib/printEstimator'
import type { LivePricing } from '../../lib/printEstimator'
import { ChevronDown, ChevronRight } from 'lucide-react'

interface EstimateResult {
  time: { hours: number; minutes: number }
  filament: { grams: number; meters: number; cost: number }
}

interface BoundingBox {
  width?: number
  depth?: number
  height?: number
}

interface CostRange {
  low: number
  mid: number
  high: number
  currency: string
  source: string
}

interface EstimateRowsProps {
  est: EstimateResult
  t: (key: string) => string
  costRange?: CostRange | null
}

function formatCurrency(amount: number, currency: string): string {
  const symbol = currency === 'MXN' ? '$' : currency === 'USD' ? '$' : ''
  const suffix = currency === 'MXN' ? ' MXN' : currency === 'USD' ? ' USD' : ` ${currency}`
  return `${symbol}${amount.toFixed(2)}${suffix}`
}

function EstimateRows({ est, t, costRange }: EstimateRowsProps) {
  return (
    <>
      <div className="flex justify-between">
        <span className="text-muted-foreground">{t('print.time')}:</span>
        <span className="font-medium">{est.time.hours > 0 ? `${est.time.hours}h ` : ''}{est.time.minutes}m</span>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">{t('print.weight')}:</span>
        <span className="font-medium">{est.filament.grams}g</span>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">{t('print.length')}:</span>
        <span className="font-medium">{est.filament.meters}m</span>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">{t('print.cost')}:</span>
        {costRange ? (
          <span className="font-medium text-right">
            {formatCurrency(costRange.low, costRange.currency)}
            {' – '}
            {formatCurrency(costRange.high, costRange.currency)}
          </span>
        ) : (
          <span className="font-medium">~${est.filament.cost}</span>
        )}
      </div>
    </>
  )
}

interface PrintEstimateOverlayProps {
  volumeMm3?: number
  boundingBox?: BoundingBox
  perPartData?: Record<string, { volumeMm3: number; boundingBox: BoundingBox }>
  inline?: boolean
}

export default function PrintEstimateOverlay({ volumeMm3, boundingBox, perPartData, inline = false }: PrintEstimateOverlayProps) {
  const { t, language } = useLanguage()
  const { manifest } = useManifest()
  const manifestMaterials = (manifest as Record<string, unknown>)?.materials || null
  const [material, setMaterial] = useState((manifest as Record<string, unknown>)?.print_estimation ? ((manifest as Record<string, unknown>).print_estimation as Record<string, unknown>)?.default_material as string || 'pla' : 'pla')
  const [infill, setInfill] = useState((manifest as Record<string, unknown>)?.print_estimation ? ((manifest as Record<string, unknown>).print_estimation as Record<string, unknown>)?.default_infill as number ?? 0.20 : 0.20)
  const [infillPattern, setInfillPattern] = useState('grid')
  const [nozzleDiameter, setNozzleDiameter] = useState(0.4)
  const [breakdownOpen, setBreakdownOpen] = useState(false)
  const [livePricing, setLivePricing] = useState<LivePricing | null>(null)
  useEffect(() => {
    fetchMaterialPricing(material).then(setLivePricing)
  }, [material])

  const materials = useMemo(() => getMaterialProfiles(manifestMaterials as never), [manifestMaterials])
  const materialLookup = useMemo(() => buildMaterialLookup(manifestMaterials as never), [manifestMaterials])
  const infillPatterns = useMemo(() => getInfillPatterns(), [])
  const nozzleDiameters = useMemo(() => getNozzleDiameters(), [])

  const estimate = useMemo(() => {
    if (!volumeMm3 || volumeMm3 <= 0 || !boundingBox) return null
    return estimatePrint(volumeMm3, boundingBox as never, material, { infill, infillPattern, nozzleDiameter }, materialLookup as never) as EstimateResult
  }, [volumeMm3, boundingBox, material, infill, infillPattern, nozzleDiameter, materialLookup])

  // Per-part estimates: compute independently for each part using its own bbox height
  const partEstimates = useMemo(() => {
    if (!perPartData || Object.keys(perPartData).length <= 1) return null
    return Object.entries(perPartData).map(([partType, { volumeMm3: pVol, boundingBox: pBox }]) => {
      const partDef = manifest?.parts?.find((p: Record<string, unknown>) => p.id === partType)
      const label = partDef?.label
        ? (typeof partDef.label === 'object' ? ((partDef.label as Record<string, string>)[language] || (partDef.label as Record<string, string>).en || partType) : partDef.label as string)
        : partType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      const est = pVol > 0 && pBox ? estimatePrint(pVol, pBox as never, material, { infill, infillPattern, nozzleDiameter }, materialLookup as never) as EstimateResult : null
      return { partType, label, est }
    }).filter(p => p.est !== null) as Array<{ partType: string; label: string; est: EstimateResult }>
  }, [perPartData, material, infill, infillPattern, nozzleDiameter, materialLookup, manifest, language])

  const costRange = useMemo(() => {
    if (!estimate) return null
    return computeCostRange(estimate.filament.grams, livePricing)
  }, [estimate, livePricing])

  if (!volumeMm3 || volumeMm3 <= 0) return null
  if (!estimate) return null

  const { time, filament } = estimate

  if (inline) {
    return (
      <div role="status" aria-label="Print estimate" className="p-3 text-xs space-y-2 h-full pb-safe">
        <div className="font-semibold text-sm text-foreground">{t('print.title')}</div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <label htmlFor="pe-material-inline" className="text-muted-foreground shrink-0">{t('print.material')}:</label>
          <select
            id="pe-material-inline"
            className="bg-background border border-border rounded px-2 py-2 md:py-0.5 text-base md:text-xs min-h-[44px] md:min-h-0 flex-1 min-w-0"
            value={material}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setMaterial(e.target.value)}
          >
            {materials.map((m: Record<string, unknown>) => (
              <option key={m.id as string} value={m.id as string}>{m.name as string}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <label htmlFor="pe-infill-inline" className="text-muted-foreground shrink-0">{t('print.infill')}:</label>
          <select
            id="pe-infill-inline"
            className="bg-background border border-border rounded px-2 py-2 md:py-0.5 text-base md:text-xs min-h-[44px] md:min-h-0 flex-1 min-w-0"
            value={infill}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setInfill(parseFloat(e.target.value))}
          >
            <option value={0.10}>10%</option>
            <option value={0.15}>15%</option>
            <option value={0.20}>20%</option>
            <option value={0.30}>30%</option>
            <option value={0.50}>50%</option>
            <option value={1.00}>100%</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <label htmlFor="pe-pattern-inline" className="text-muted-foreground shrink-0">{t('print.pattern') || 'Pattern'}:</label>
          <select
            id="pe-pattern-inline"
            className="bg-background border border-border rounded px-2 py-2 md:py-0.5 text-base md:text-xs min-h-[44px] md:min-h-0 flex-1 min-w-0"
            value={infillPattern}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setInfillPattern(e.target.value)}
          >
            {infillPatterns.map((p: Record<string, unknown>) => (
              <option key={p.id as string} value={p.id as string}>{p.name as string}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <label htmlFor="pe-nozzle-inline" className="text-muted-foreground shrink-0">{t('print.nozzle') || 'Nozzle'}:</label>
          <select
            id="pe-nozzle-inline"
            className="bg-background border border-border rounded px-2 py-2 md:py-0.5 text-base md:text-xs min-h-[44px] md:min-h-0 flex-1 min-w-0"
            value={nozzleDiameter}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setNozzleDiameter(parseFloat(e.target.value))}
          >
            {nozzleDiameters.map((n: Record<string, unknown>) => (
              <option key={n.value as number} value={n.value as number}>{n.label as string}</option>
            ))}
          </select>
        </div>

        {/* Prices display in the pricing source's own currency. A toggle used
            to relabel MXN values as USD (and vice versa) without converting —
            there is no FX rate anywhere in the system, so relabeling was the
            only thing it could do. Until an FX layer exists, the label always
            tells the truth about the number next to it. */}
        {costRange && (
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">{t('print.currency') || 'Currency'}:</span>
            <span className="text-xs font-medium">{costRange.currency}</span>
          </div>
        )}

        {/* Aggregate total */}
        <div className="border-t border-border pt-2 space-y-1">
          {partEstimates && (
            <div className="text-muted-foreground font-medium mb-1">Total</div>
          )}
          <EstimateRows est={estimate} t={t} costRange={costRange} />
          {costRange?.source === 'forgesight' && (
            <div className="text-[10px] text-primary/70 mt-1 font-medium">
              Market pricing via ForgeSight
            </div>
          )}
          <div className="text-[10px] text-muted-foreground/60 mt-1 italic">
            {costRange ? (t('print.disclaimer_time') || 'Time estimate \u00b130%') : (t('print.disclaimer') || 'Estimate (\u00b130% for typical parts)')}
          </div>
        </div>

        {/* Per-part breakdown accordion */}
        {partEstimates && partEstimates.length > 0 && (
          <div className="border-t border-border pt-2">
            <button
              onClick={() => setBreakdownOpen(o => !o)}
              className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors w-full font-medium"
              aria-expanded={breakdownOpen}
            >
              {breakdownOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              Per Part
            </button>
            {breakdownOpen && (
              <div className="mt-2 space-y-3">
                {partEstimates.map(({ partType, label, est }) => (
                  <div key={partType} className="space-y-1">
                    <div className="font-medium text-foreground truncate" title={label}>{label}</div>
                    <EstimateRows est={est} t={t} />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  // Legacy absolute overlay (kept for backward compat)
  return (
    <div role="status" aria-label="Print estimate" className="absolute bottom-2 right-2 pb-safe bg-card border border-border rounded-lg p-3 text-xs space-y-2 min-w-[180px] z-10">
      <div className="font-semibold text-sm">{t('print.title')}</div>

      <div className="flex items-center gap-2">
        <label htmlFor="pe-material" className="text-muted-foreground">{t('print.material')}:</label>
        <select
          id="pe-material"
          className="bg-background border border-border rounded px-2 py-2 md:py-0.5 text-base md:text-xs min-h-[44px] md:min-h-0"
          value={material}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setMaterial(e.target.value)}
        >
          {materials.map((m: Record<string, unknown>) => (
            <option key={m.id as string} value={m.id as string}>{m.name as string}</option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <label htmlFor="pe-infill" className="text-muted-foreground">{t('print.infill')}:</label>
        <select
          id="pe-infill"
          className="bg-background border border-border rounded px-2 py-2 md:py-0.5 text-base md:text-xs min-h-[44px] md:min-h-0"
          value={infill}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setInfill(parseFloat(e.target.value))}
        >
          <option value={0.10}>10%</option>
          <option value={0.15}>15%</option>
          <option value={0.20}>20%</option>
          <option value={0.30}>30%</option>
          <option value={0.50}>50%</option>
          <option value={1.00}>100%</option>
        </select>
      </div>

      <div className="border-t border-border pt-2 space-y-1">
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('print.time')}:</span>
          <span className="font-medium">
            {time.hours > 0 ? `${time.hours}h ` : ''}{time.minutes}m
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('print.weight')}:</span>
          <span className="font-medium">{filament.grams}g</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('print.length')}:</span>
          <span className="font-medium">{filament.meters}m</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('print.cost')}:</span>
          <span className="font-medium">~${filament.cost}</span>
        </div>
      </div>
    </div>
  )
}
