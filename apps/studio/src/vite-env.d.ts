/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Build-time render-mode pin: 'backend' | 'wasm'.
   * Overridden per-session by the `?render=` query param. Any other value is
   * ignored — see parseRenderMode in services/engine/renderService.ts.
   */
  readonly VITE_RENDER_MODE?: string
}
