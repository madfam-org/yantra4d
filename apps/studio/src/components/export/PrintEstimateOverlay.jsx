import { useState, useMemo } from 'react'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useManifest } from '../../contexts/project/ManifestProvider'
import { estimatePrint, getMaterialProfiles, buildMaterialLookup } from '../../lib/printEstimator'
import { ChevronDown, ChevronRight } from 'lucide-react'

/**
 * Shared row set for time/weight/length/cost — declared at module scope to satisfy
 * react-hooks/static-components (no components created during render).
 */
function EstimateRows({ est, t }) {
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
        <span className="font-medium">~${est.filament.cost}</span>
      </div>
    </>
  )
}

/**
 * Shows print-time and filament estimates for the current model.
 * `inline` prop: render as a sidebar panel instead of an absolute overlay.
 * `perPartData`: map of partType → {volumeMm3, boundingBox} for per-part breakdown.
 */
export default function PrintEstimateOverlay({ volumeMm3, boundingBox, perPartData, inline = false }) {
  const { t, language } = useLanguage()
  const { manifest } = useManifest()
  const manifestMaterials = manifest?.materials || null
  const [material, setMaterial] = useState(manifest?.print_estimation?.default_material || 'pla')
  const [infill, setInfill] = useState(manifest?.print_estimation?.default_infill ?? 0.20)
  const [breakdownOpen, setBreakdownOpen] = useState(false)
  const materials = useMemo(() => getMaterialProfiles(manifestMaterials), [manifestMaterials])
  const materialLookup = useMemo(() => buildMaterialLookup(manifestMaterials), [manifestMaterials])

  const estimate = useMemo(() => {
    if (!volumeMm3 || volumeMm3 <= 0 || !boundingBox) return null
    return estimatePrint(volumeMm3, boundingBox, material, { infill }, materialLookup)
  }, [volumeMm3, boundingBox, material, infill, materialLookup])

  // Per-part estimates: compute independently for each part using its own bbox height
  const partEstimates = useMemo(() => {
    if (!perPartData || Object.keys(perPartData).length <= 1) return null
    return Object.entries(perPartData).map(([partType, { volumeMm3: pVol, boundingBox: pBox }]) => {
      const partDef = manifest?.parts?.find(p => p.id === partType)
      const label = partDef?.label
        ? (typeof partDef.label === 'object' ? (partDef.label[language] || partDef.label.en || partType) : partDef.label)
        : partType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      const est = pVol > 0 && pBox ? estimatePrint(pVol, pBox, material, { infill }, materialLookup) : null
      return { partType, label, est }
    }).filter(p => p.est !== null)
  }, [perPartData, material, infill, materialLookup, manifest, language])

  if (!volumeMm3 || volumeMm3 <= 0) return null
  if (!estimate) return null

  const { time, filament } = estimate

  if (inline) {
    return (
      <div role="status" aria-label="Print estimate" className="p-3 text-xs space-y-2 h-full">
        <div className="font-semibold text-sm text-foreground">{t('print.title')}</div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <label htmlFor="pe-material-inline" className="text-muted-foreground shrink-0">{t('print.material')}:</label>
          <select
            id="pe-material-inline"
            className="bg-background border border-border rounded px-1 py-0.5 text-xs flex-1 min-w-0"
            value={material}
            onChange={e => setMaterial(e.target.value)}
          >
            {materials.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <label htmlFor="pe-infill-inline" className="text-muted-foreground shrink-0">{t('print.infill')}:</label>
          <select
            id="pe-infill-inline"
            className="bg-background border border-border rounded px-1 py-0.5 text-xs flex-1 min-w-0"
            value={infill}
            onChange={e => setInfill(parseFloat(e.target.value))}
          >
            <option value={0.10}>10%</option>
            <option value={0.15}>15%</option>
            <option value={0.20}>20%</option>
            <option value={0.30}>30%</option>
            <option value={0.50}>50%</option>
            <option value={1.00}>100%</option>
          </select>
        </div>

        {/* Aggregate total */}
        <div className="border-t border-border pt-2 space-y-1">
          {partEstimates && (
            <div className="text-muted-foreground font-medium mb-1">Total</div>
          )}
          <EstimateRows est={estimate} t={t} />
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
    <div role="status" aria-label="Print estimate" className="absolute bottom-2 right-2 bg-card border border-border rounded-lg p-3 text-xs space-y-2 min-w-[180px] z-10">
      <div className="font-semibold text-sm">{t('print.title')}</div>

      <div className="flex items-center gap-2">
        <label htmlFor="pe-material" className="text-muted-foreground">{t('print.material')}:</label>
        <select
          id="pe-material"
          className="bg-background border border-border rounded px-1 py-0.5 text-xs"
          value={material}
          onChange={e => setMaterial(e.target.value)}
        >
          {materials.map(m => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <label htmlFor="pe-infill" className="text-muted-foreground">{t('print.infill')}:</label>
        <select
          id="pe-infill"
          className="bg-background border border-border rounded px-1 py-0.5 text-xs"
          value={infill}
          onChange={e => setInfill(parseFloat(e.target.value))}
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
