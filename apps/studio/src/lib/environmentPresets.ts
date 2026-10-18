/**
 * Self-hosted environment maps for `@react-three/drei`'s `<Environment>`.
 *
 * `<Environment preset="city">` fetches its HDR from raw.githack.com at runtime. The Studio's
 * CSP allows `connect-src 'self'` plus the API, auth and landing origins only, so that fetch is
 * blocked in production and the viewer's ErrorBoundary swallowed the whole canvas (every project
 * page showed "Could not load potsdamer_platz_1k.hdr", 2026-10-18). The same files are served
 * from `public/hdri/` instead; this is drei's own preset → file table.
 */
export const ENVIRONMENT_HDRI_PATH = '/hdri/'

export const ENVIRONMENT_PRESET_FILES = {
  apartment: 'lebombo_1k.hdr',
  city: 'potsdamer_platz_1k.hdr',
  dawn: 'kiara_1_dawn_1k.hdr',
  forest: 'forest_slope_1k.hdr',
  lobby: 'st_fagans_interior_1k.hdr',
  night: 'dikhololo_night_1k.hdr',
  park: 'rooitou_park_1k.hdr',
  studio: 'studio_small_03_1k.hdr',
  sunset: 'venice_sunset_1k.hdr',
  warehouse: 'empty_warehouse_01_1k.hdr',
} as const

export type EnvironmentPresetName = keyof typeof ENVIRONMENT_PRESET_FILES

export const DEFAULT_ENVIRONMENT_PRESET: EnvironmentPresetName = 'city'

export function isEnvironmentPreset(name: string): name is EnvironmentPresetName {
  return Object.prototype.hasOwnProperty.call(ENVIRONMENT_PRESET_FILES, name)
}

/** The HDR file for a preset name; an unknown name falls back to the default (city). */
export function environmentFile(name: string): string {
  return ENVIRONMENT_PRESET_FILES[isEnvironmentPreset(name) ? name : DEFAULT_ENVIRONMENT_PRESET]
}
