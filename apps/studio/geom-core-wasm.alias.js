/**
 * Vite/Vitest alias for the geom-core WASM binary.
 *
 * `@madfam/geom-core` exports only `.` and `./wasm`, so its `.wasm` file
 * cannot be imported by subpath. The Emscripten loader also cannot locate the
 * binary from inside a bundled chunk. This alias maps the virtual specifier
 * `@madfam/geom-core/wasm-binary` (with any `?url` query) to the file next to
 * the exported loader, so `import('@madfam/geom-core/wasm-binary?url')` makes
 * Vite emit it as a hashed asset and returns its URL (see
 * src/lib/geomCoreBrowser.ts). Imported only when VITE_GEOM_CORE_BROWSER is on.
 */
import { createRequire } from 'module'
import path from 'path'

const require = createRequire(import.meta.url)
const GEOM_CORE_WASM = path.join(path.dirname(require.resolve('@madfam/geom-core/wasm')), 'geom-core.wasm')

export const geomCoreWasmAlias = {
  find: /^@madfam\/geom-core\/wasm-binary(\?.*)?$/,
  replacement: `${GEOM_CORE_WASM}$1`,
}
