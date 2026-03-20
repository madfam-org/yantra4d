/**
 * Shared OpenSCAD output phase detection utilities.
 * Used by both renderService (main thread) and openscad-worker (Web Worker).
 * NOTE: This module must remain pure JS/TS (no DOM, no React) for worker compatibility.
 */

/**
 * Detect the progress phase from an OpenSCAD output line.
 */
export function detectPhase(line: string): string | null {
  if (line.includes('Compiling')) return 'compiling'
  if (line.includes('CGAL')) return 'cgal'
  if (line.includes('Rendering') || line.includes('Geometries')) return 'rendering'
  if (line.includes('Parsing')) return 'geometry'
  return null
}

/**
 * Check if a line is worth logging (contains significant OpenSCAD output).
 */
export function isLogWorthy(line: string): boolean {
  return line.includes('Compiling') || line.includes('Parsing') ||
    line.includes('CGAL') || line.includes('Geometries') ||
    line.includes('Rendering') || line.includes('Total') ||
    line.includes('Simple:')
}
