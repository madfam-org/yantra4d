/**
 * Print-time and filament estimator.
 * Computes estimates from STL geometry volume + slicer heuristics.
 *
 * Material profiles define density, print speed, and layer-dependent factors.
 */

const MATERIAL_PROFILES = {
  pla: {
    name: 'PLA',
    density: 1.24,       // g/cm³
    speed: 50,           // mm/s typical
    layerHeight: 0.2,    // mm default
    costPerKg: 20,       // USD approximate
    nozzleDiameter: 0.4, // mm
  },
  petg: {
    name: 'PETG',
    density: 1.27,
    speed: 40,
    layerHeight: 0.2,
    costPerKg: 22,
    nozzleDiameter: 0.4,
  },
  abs: {
    name: 'ABS',
    density: 1.04,
    speed: 45,
    layerHeight: 0.2,
    costPerKg: 18,
    nozzleDiameter: 0.4,
  },
  tpu: {
    name: 'TPU',
    density: 1.21,
    speed: 25,
    layerHeight: 0.2,
    costPerKg: 35,
    nozzleDiameter: 0.4,
  },
}

/**
 * Compute volume of an STL geometry from Three.js BufferGeometry.
 * Uses the signed volume of tetrahedra method.
 * @param {BufferGeometry} geometry - Three.js geometry
 * @returns {number} Volume in mm³
 */
export function computeVolumeMm3(geometry) {
  if (!geometry?.attributes?.position) return 0

  const pos = geometry.attributes.position
  const index = geometry.index
  let volume = 0

  const getVertex = (i) => ({
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
 * @param {BufferGeometry} geometry
 * @returns {{ width: number, depth: number, height: number }} in mm
 */
export function computeBoundingBox(geometry) {
  if (!geometry) return { width: 0, depth: 0, height: 0 }
  geometry.computeBoundingBox()
  const box = geometry.boundingBox
  return {
    width: box.max.x - box.min.x,
    height: box.max.z - box.min.z,  // Z-up convention
    depth: box.max.y - box.min.y,
  }
}

/**
 * Compute the volumetric centroid of a geometry.
 * Uses the signed volume of tetrahedra method.
 * @param {BufferGeometry} geometry
 * @returns {{ x: number, y: number, z: number }} Centroid coordinates
 */
export function computeCentroid(geometry) {
  if (!geometry?.attributes?.position) return { x: 0, y: 0, z: 0 }

  const pos = geometry.attributes.position
  const index = geometry.index
  let volume = 0
  let cx = 0, cy = 0, cz = 0

  const getVertex = (i) => ({
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
 * @param {number} volumeMm3 - Part volume in mm³
 * @param {{ width: number, depth: number, height: number }} bbox - Bounding box in mm
 * @param {string} materialId - Material profile key
 * @param {object} [overrides] - Optional overrides for layer height, infill, etc.
 * @returns {{ time: { hours: number, minutes: number }, filament: { grams: number, meters: number, cost: number }, material: string }}
 */
export function estimatePrint(volumeMm3, bbox, materialId = 'pla', overrides = {}, materialLookup = null) {
  const profiles = materialLookup || MATERIAL_PROFILES
  const profile = profiles[materialId] || profiles.pla || MATERIAL_PROFILES.pla
  const layerHeight = overrides.layerHeight || profile.layerHeight
  const infill = overrides.infill ?? 0.20  // 20% default
  const speed = overrides.speed || profile.speed

  // Estimate actual printed volume (walls + infill)
  // Rough heuristic: shell volume + infill * interior
  const shellVolume = volumeMm3 * 0.3  // ~30% is shell
  const infillVolume = volumeMm3 * 0.7 * infill
  const printedVolume = shellVolume + infillVolume  // mm³

  // Filament weight
  const volumeCm3 = printedVolume / 1000
  const grams = volumeCm3 * profile.density

  // Filament length (1.75mm diameter)
  const filamentDiameter = 1.75  // mm
  const crossSection = Math.PI * (filamentDiameter / 2) ** 2  // mm²
  const meters = printedVolume / crossSection / 1000

  // Cost
  const cost = (grams / 1000) * profile.costPerKg

  // Time estimation (simplified)
  // layers = height / layer_height
  // time per layer ≈ (perimeter + infill_travel) / speed
  const layers = bbox.height / layerHeight
  const perimeterPerLayer = 2 * (bbox.width + bbox.depth)  // outer perimeter mm
  const infillTravelPerLayer = bbox.width * bbox.depth * infill / profile.nozzleDiameter * 0.5
  const travelPerLayer = perimeterPerLayer + infillTravelPerLayer
  const totalTravelMm = travelPerLayer * layers
  const printSeconds = totalTravelMm / speed
  // Add overhead: homing, heating, travel moves (~10%)
  const totalSeconds = printSeconds * 1.1

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
 * @param {Array|null} manifestMaterials - Optional materials from project manifest
 */
export function getMaterialProfiles(manifestMaterials) {
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
 * Build a merged profile lookup that includes manifest materials.
 * @param {Array|null} manifestMaterials
 * @returns {Object} materialId → profile
 */
export function buildMaterialLookup(manifestMaterials) {
  const lookup = { ...MATERIAL_PROFILES }
  if (manifestMaterials) {
    for (const m of manifestMaterials) {
      lookup[m.id] = {
        name: m.name,
        density: m.density,
        speed: 50 * (m.print_speed_factor || 1),
        layerHeight: 0.2,
        costPerKg: m.cost_per_kg,
        nozzleDiameter: 0.4,
      }
    }
  }
  return lookup
}
