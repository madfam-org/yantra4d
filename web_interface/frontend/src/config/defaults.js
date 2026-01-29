/**
 * Centralized defaults and mode mappings — single source of truth.
 */

export const DEFAULTS = {
  params: {
    size: 20.0,
    thick: 2.5,
    rod_D: 3.0,
    show_base: true,
    show_walls: true,
    show_mech: true,
    rows: 8,
    cols: 8,
    rod_extension: 10,
  },
  colors: {
    bottom: '#ffffff',
    top: '#000000',
    rods: '#808080',
    stoppers: '#ffd700',
    main: '#e5e7eb',
  },
}

/** Which color pickers to show per mode */
export const MODE_COLORS_MAP = {
  unit: ['main'],
  assembly: ['bottom', 'top'],
  grid: ['bottom', 'top', 'rods', 'stoppers'],
}

/** SCAD file per mode */
export const MODE_SCAD_MAP = {
  unit: 'half_cube.scad',
  assembly: 'assembly.scad',
  grid: 'tablaco.scad',
}
