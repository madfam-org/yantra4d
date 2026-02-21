# Yantra4D WASM / Offline Mode

Yantra4D features a robust **dual-rendering architecture** that allows the application to function even when the backend API is unavailable or unreachable. This is achieved through a client-side OpenSCAD WebAssembly (WASM) implementation.

## Overview

The system automatically detects backend availability and switches modes seamlessly:

1.  **Backend Mode (Default)**: Sends parameters to the Python/Flask API, which runs the native OpenSCAD CLI. This is typically faster for complex models.
2.  **WASM Mode (Fallback)**: Runs OpenSCAD entirely within the browser using a Web Worker. This enables zero-latency offline usage and static deployments (e.g., GitHub Pages).

## Architecture

The logic resides principally in `apps/studio/src/services/renderService.js` and `apps/studio/src/services/openscad-worker.js`.

### Detection Mechanism
On application start (and before renders), `renderService.js` probes the backend health endpoint:
```javascript
// apps/studio/src/services/backendDetection.js
export async function isBackendAvailable() {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { method: 'HEAD', timeout: 2000 })
    return res.ok
  } catch {
    return false
  }
}
```

### The Web Worker
The WASM worker (`openscad-worker.js`) manages the OpenSCAD instance to prevent the main thread from freezing during heavy computations.

-   **Library**: Uses `openscad-wasm` (based on OpenSCAD master branch).
-   **Isolation**: Every render spins up a *fresh* WASM instance to avoid memory corruption issues (a known quirk of the EMSCRIPTEN build).
-   **File System**: Source `.scad` files are fetched once, cached in memory, and written to the worker's virtual filesystem for each render.

## Enabling WASM Mode

### Automatic Fallback
Simply stop the backend server. The Studio will visually indicate offline mode (often by hiding backend-specific features like GitHub sync) but rendering will continue to work.

### Forcing WASM Mode
You can force WASM mode for testing by blocking the API rendering or building a static version of the site without `VITE_API_BASE_URL`.

## Limitations

| Feature | Backend Mode | WASM Mode |
| :--- | :--- | :--- |
| **Performance** | Native speed (fast) | ~3-5x slower |
| **Memory** | Server RAM limit | Browser tab limit (~4GB) |
| **Libraries** | Full system access | Virtual FS only |
| **Export** | STL, 3MF, OFF, PNG | STL only (currently) |
| **Caching** | Persistent Redis/Disk | Ephemeral (Session) |

## Troubleshooting

-   **"Out of Memory"**: Complex models with high `fn` (smoothness) may crash the browser tab. Reduce `fn` or switch to backend mode.
-   **"SharedArrayBuffer"**: Ensure your server sends `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` headers, which are required for high-performance WASM threading (though `openscad-wasm` single-threaded builds work without them).
