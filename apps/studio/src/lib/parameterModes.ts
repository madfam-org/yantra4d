/**
 * Which modes a manifest parameter belongs to.
 *
 * The manifest schema (packages/schemas/project-manifest.schema.json) gives a
 * parameter two equivalent scoping lists: `visible_in_modes` and `modes`.
 * Cartridges use both: in the pinned commons (512 manifests, measured
 * 2026-10-18) 3979 parameters across 465 cartridges are scoped by `modes`
 * alone, 249 by `visible_in_modes` alone and 44 by both. Reading only
 * `visible_in_modes` treated every `modes`-scoped parameter as global, so
 * switching gridfinity from `bin` to `cup` kept the bin sliders on screen next
 * to the cup ones.
 *
 * `visible_in_modes` wins when both are present (it is the Studio's original
 * field); `undefined` means the parameter is not scoped and shows in every mode.
 */
export interface ModeScoped {
  visible_in_modes?: unknown
  modes?: unknown
}

export function parameterModes(param: ModeScoped): string[] | undefined {
  const scope = param.visible_in_modes ?? param.modes
  return Array.isArray(scope) ? (scope as string[]) : undefined
}

export function isParameterInMode(param: ModeScoped, modeId: string): boolean {
  const scope = parameterModes(param)
  return !scope || scope.includes(modeId)
}
