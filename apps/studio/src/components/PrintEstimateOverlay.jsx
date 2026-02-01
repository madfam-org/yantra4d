import { useState, useMemo } from 'react'
import { useLanguage } from '../contexts/LanguageProvider'
import { useManifest } from '../contexts/ManifestProvider'
import { estimatePrint, getMaterialProfiles, buildMaterialLookup } from '../lib/printEstimator'

/**
 * Overlay showing print-time and filament estimates for current model.
 * Receives geometry stats computed by parent (volume in mm³ + bounding box).
 */
export default function PrintEstimateOverlay({ volumeMm3, boundingBox }) {
  const { t } = useLanguage()
  const { manifest } = useManifest()
  const manifestMaterials = manifest?.materials || null
  const [material, setMaterial] = useState(manifest?.print_estimation?.default_material || 'pla')
  const [infill, setInfill] = useState(manifest?.print_estimation?.default_infill ?? 0.20)
  const materials = useMemo(() => getMaterialProfiles(manifestMaterials), [manifestMaterials])
  const materialLookup = useMemo(() => buildMaterialLookup(manifestMaterials), [manifestMaterials])

  const estimate = useMemo(() => {
    if (!volumeMm3 || volumeMm3 === 0 || !boundingBox) return null
    return estimatePrint(volumeMm3, boundingBox, material, { infill }, materialLookup)
  }, [volumeMm3, boundingBox, material, infill, materialLookup])

  if (!estimate) return null

  const { time, filament } = estimate

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
