/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Build-time render-mode pin: 'backend' | 'wasm'.
   * Overridden per-session by the `?render=` query param. Any other value is
   * ignored — see parseRenderMode in services/engine/renderService.ts.
   */
  readonly VITE_RENDER_MODE?: string
  /**
   * Experimental: '1' routes mesh parse/bbox/volume/centroid through the
   * @madfam/geom-core WASM (default off). Overridden per-session by
   * `?geomcore=1|0` — see src/lib/geomCoreBrowser.ts.
   */
  readonly VITE_GEOM_CORE_BROWSER?: string
}

/** Virtual specifier for the geom-core .wasm asset (geom-core-wasm.alias.js). */
declare module '@madfam/geom-core/wasm-binary?url' {
  const url: string
  export default url
}
