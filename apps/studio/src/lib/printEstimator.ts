/**
 * Print-time and filament estimator.
 * Computes estimates from STL geometry volume + slicer heuristics.
 *
 * Material profiles define density, print speed, and layer-dependent factors.
 */

interface MaterialProfile {
  name: string
  density: number       // g/cm3
  speed: number         // mm/s typical
  layerHeight: number   // mm default
  costPerKg: number     // USD approximate
  nozzleDiameter: number // mm
  preheatMinutes: number // minutes before printing starts
}

type MaterialProfileMap = Record<string, MaterialProfile>

const MATERIAL_PROFILES: MaterialProfileMap = {
  pla: {
    name: 'PLA',
    density: 1.24,        // g/cm³
    speed: 50,            // mm/s typical
    layerHeight: 0.2,     // mm default
    costPerKg: 20,        // USD approximate
    nozzleDiameter: 0.4,  // mm
    preheatMinutes: 2,    // minutes for bed/nozzle warmup
  },
  petg: {
    name: 'PETG',
    density: 1.27,
    speed: 40,
    layerHeight: 0.2,
    costPerKg: 22,
    nozzleDiameter: 0.4,
    preheatMinutes: 5,
  },
  abs: {
    name: 'ABS',
    density: 1.04,
    speed: 45,
    layerHeight: 0.2,
    costPerKg: 18,
    nozzleDiameter: 0.4,
    preheatMinutes: 8,
  },
  tpu: {
    name: 'TPU',
    density: 1.21,
    speed: 25,
    layerHeight: 0.2,
    costPerKg: 35,
    nozzleDiameter: 0.4,
    preheatMinutes: 3,
  },
}

/**
 * Infill pattern speed factors — relative to baseline rectilinear/grid speed.
 * Gyroid is slower (curved paths), lightning is faster (sparse fills).
 */
const INFILL_SPEED_FACTORS: Record<string, number> = {
  grid: 1.0,
  rectilinear: 1.0,
  triangles: 0.95,
  gyroid: 0.85,
  cubic: 0.90,
  honeycomb: 0.80,
  lightning: 1.3,
}

interface Vertex {
  x: number
  y: number
  z: number
}

interface BoundingBox {
  width: number
  depth: number
  height: number
}

interface PrintEstimate {
  time: { hours: number; minutes: number }
  filament: { grams: number; meters: number; cost: number }
  material: string
}

interface PrintOverrides {
  layerHeight?: number
  infill?: number
  speed?: number
  nozzleDiameter?: number
  infillPattern?: string
  overhangPct?: number   // 0-1, from backend overhang analysis
}

interface ManifestMaterial {
  id: string
  name: string
  density: number
  print_speed_factor?: number
  cost_per_kg: number
}

interface MaterialOption {
  id: string
  name: string
}

/**
 * Minimal geometry interface matching Three.js BufferGeometry shape.
 * Only the properties actually accessed by this module.
 */
interface GeometryLike {
  attributes: {
    position: {
      count: number
      getX(index: number): number
      getY(index: number): number
      getZ(index: number): number
    }
  }
  index: {
    count: number
    getX(index: number): number
  } | null
  computeBoundingBox(): void
  boundingBox: {
    min: Vertex
    max: Vertex
  } | null
}

/**
 * Compute volume of an STL geometry from Three.js BufferGeometry.
 * Uses the signed volume of tetrahedra method.
 */
export function computeVolumeMm3(geometry: GeometryLike | null | undefined): number {
  if (!geometry?.attributes?.position) return 0

  const pos = geometry.attributes.position
  const index = geometry.index
  let volume = 0

  const getVertex = (i: number): Vertex => ({
    x: pos.getX(i),
    y: pos.getY(i),
    z: pos.getZ(i),
  })

  const triCount = index ? index.count / 3 : pos.count / 3

  for (let i = 0; i < triCount; i++) {
    const i0 = index ? index.getX(i * 3) : i * 3
    const i1 = index ? index.getX(i * 3 + 1) : i * 3 + 1
    const i2 = index ? index.getX(i * 3 + 2) : i * 3 + 2

    const v0 = getVertex(i0)
    const v1 = getVertex(i1)
    const v2 = getVertex(i2)

    // Signed volume of tetrahedron formed with origin
    volume += (
      v0.x * (v1.y * v2.z - v2.y * v1.z) -
      v1.x * (v0.y * v2.z - v2.y * v0.z) +
      v2.x * (v0.y * v1.z - v1.y * v0.z)
    ) / 6.0
  }

  return Math.abs(volume)
}

/**
 * Compute bounding box dimensions from geometry.
 */
export function computeBoundingBox(geometry: GeometryLike | null | undefined): BoundingBox {
  if (!geometry) return { width: 0, depth: 0, height: 0 }
  geometry.computeBoundingBox()
  const box = geometry.boundingBox!
  return {
    width: box.max.x - box.min.x,
    height: box.max.z - box.min.z,  // Z-up convention
    depth: box.max.y - box.min.y,
  }
}

/**
 * Compute the volumetric centroid of a geometry.
 * Uses the signed volume of tetrahedra method.
 */
export function computeCentroid(geometry: GeometryLike | null | undefined): Vertex {
  if (!geometry?.attributes?.position) return { x: 0, y: 0, z: 0 }

  const pos = geometry.attributes.position
  const index = geometry.index
  let volume = 0
  let cx = 0, cy = 0, cz = 0

  const getVertex = (i: number): Vertex => ({
    x: pos.getX(i),
    y: pos.getY(i),
    z: pos.getZ(i),
  })

  const triCount = index ? index.count / 3 : pos.count / 3

  for (let i = 0; i < triCount; i++) {
    const i0 = index ? index.getX(i * 3) : i * 3
    const i1 = index ? index.getX(i * 3 + 1) : i * 3 + 1
    const i2 = index ? index.getX(i * 3 + 2) : i * 3 + 2

    const v0 = getVertex(i0)
    const v1 = getVertex(i1)
    const v2 = getVertex(i2)

    // Signed volume of tetrahedron formed with origin
    const vol = (
      v0.x * (v1.y * v2.z - v2.y * v1.z) -
      v1.x * (v0.y * v2.z - v2.y * v0.z) +
      v2.x * (v0.y * v1.z - v1.y * v0.z)
    ) / 6.0

    // Centroid of the tetrahedron (average of 4 vertices, 4th is 0,0,0)
    // C_tet = (v0 + v1 + v2 + 0) / 4
    const cTetX = (v0.x + v1.x + v2.x) / 4
    const cTetY = (v0.y + v1.y + v2.y) / 4
    const cTetZ = (v0.z + v1.z + v2.z) / 4

    volume += vol
    cx += cTetX * vol
    cy += cTetY * vol
    cz += cTetZ * vol
  }

  if (Math.abs(volume) < 1e-9) return { x: 0, y: 0, z: 0 }

  return {
    x: cx / volume,
    y: cy / volume,
    z: cz / volume,
  }
}

/**
 * Estimate print time and filament usage.
 */
export function estimatePrint(
  volumeMm3: number,
  bbox: BoundingBox,
  materialId: string = 'pla',
  overrides: PrintOverrides = {},
  materialLookup: MaterialProfileMap | null = null,
): PrintEstimate {
  const profiles = materialLookup || MATERIAL_PROFILES
  const profile = profiles[materialId] || profiles.pla || MATERIAL_PROFILES.pla
  const layerHeight = overrides.layerHeight || profile.layerHeight
  const infill = overrides.infill ?? 0.20  // 20% default
  const speed = overrides.speed || profile.speed
  const nozzleDiameter = overrides.nozzleDiameter || profile.nozzleDiameter
  const infillPattern = overrides.infillPattern || 'grid'
  const overhangPct = overrides.overhangPct ?? 0  // 0-1, from backend analysis
  const infillSpeedFactor = INFILL_SPEED_FACTORS[infillPattern] ?? 1.0

  // Estimate actual printed volume (walls + infill)
  // Heuristic calibrated for thin-walled functional parts:
  //   Shell contribution: walls are typically ~40% of total volume for 2-wall prints
  //   Infill contribution: remaining 60% interior scaled by infill density
  const shellVolume = volumeMm3 * 0.40  // ~40% is shell (walls + top/bottom)
  const infillVolume = volumeMm3 * 0.60 * infill
  const printedVolume = shellVolume + infillVolume  // mm³

  // Support material estimation (15% density supports for overhanging regions)
  const supportVolume = overhangPct > 0 ? volumeMm3 * overhangPct * 0.15 : 0
  const totalPrintedVolume = printedVolume + supportVolume

  // Filament weight
  const volumeCm3 = totalPrintedVolume / 1000
  const grams = volumeCm3 * profile.density

  // Filament length (1.75mm diameter standard FDM filament)
  const filamentDiameter = 1.75  // mm
  const crossSection = Math.PI * (filamentDiameter / 2) ** 2  // mm²
  const meters = totalPrintedVolume / crossSection / 1000

  // Cost
  const cost = (grams / 1000) * profile.costPerKg

  // Time estimation
  // Layers count = part height / selected layer height
  const layers = bbox.height / layerHeight
  // Perimeter travel per layer = outline × 2 sides
  const perimeterPerLayer = 2 * (bbox.width + bbox.depth)
  // Infill travel per layer:
  //   (area × infill_density) / nozzle_diameter gives total line length for one-direction passes
  //   × 0.5 accounts for bi-directional (zig-zag) infill paths avoiding double-counting
  const infillTravelPerLayer = (bbox.width * bbox.depth * infill) / nozzleDiameter * 0.5
  const travelPerLayer = perimeterPerLayer + infillTravelPerLayer
  const totalTravelMm = travelPerLayer * layers
  // Apply infill pattern speed factor
  const effectiveSpeed = speed * infillSpeedFactor
  const printSeconds = totalTravelMm / effectiveSpeed
  // Add preheat time + overhead (homing, travel moves, first layer slow-down ~15%)
  const preheatSeconds = (profile.preheatMinutes || 0) * 60
  const totalSeconds = printSeconds * 1.15 + preheatSeconds

  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.round((totalSeconds % 3600) / 60)

  return {
    time: { hours, minutes },
    filament: {
      grams: Math.round(grams * 10) / 10,
      meters: Math.round(meters * 100) / 100,
      cost: Math.round(cost * 100) / 100,
    },
    material: profile.name,
  }
}

/**
 * Get available material profiles.
 * If manifestMaterials are provided, they are prepended to the built-in list.
 */
export function getMaterialProfiles(manifestMaterials: ManifestMaterial[] | null | undefined): MaterialOption[] {
  const builtIn = Object.entries(MATERIAL_PROFILES).map(([id, profile]) => ({
    id,
    name: profile.name,
  }))
  if (!manifestMaterials || manifestMaterials.length === 0) return builtIn
  const custom = manifestMaterials.map(m => ({ id: m.id, name: m.name }))
  // Deduplicate by id, custom takes priority
  const customIds = new Set(custom.map(m => m.id))
  return [...custom, ...builtIn.filter(m => !customIds.has(m.id))]
}

/**
 * Get available infill patterns for the UI selector.
 */
export function getInfillPatterns(): { id: string; name: string }[] {
  return Object.keys(INFILL_SPEED_FACTORS).map(id => ({
    id,
    name: id.charAt(0).toUpperCase() + id.slice(1),
  }))
}

/**
 * Get common nozzle diameters for the UI selector.
 */
export function getNozzleDiameters(): { value: number; label: string }[] {
  return [
    { value: 0.2, label: '0.2mm' },
    { value: 0.4, label: '0.4mm' },
    { value: 0.6, label: '0.6mm' },
    { value: 0.8, label: '0.8mm' },
  ]
}

/**
 * Build a merged profile lookup that includes manifest materials.
 */
export function buildMaterialLookup(manifestMaterials: ManifestMaterial[] | null | undefined): MaterialProfileMap {
  const lookup: MaterialProfileMap = { ...MATERIAL_PROFILES }
  if (manifestMaterials) {
    for (const m of manifestMaterials) {
      lookup[m.id] = {
        name: m.name,
        density: m.density,
        speed: 50 * (m.print_speed_factor || 1),
        layerHeight: 0.2,
        costPerKg: m.cost_per_kg,
        nozzleDiameter: 0.4,
        preheatMinutes: 3,  // reasonable default for custom materials
      }
    }
  }
  return lookup
}
