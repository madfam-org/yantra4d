/* global Buffer */
/**
 * Playwright route interception helpers for mocking backend API responses.
 */

const MOCK_MANIFEST = {
  project: { name: 'Test Project', slug: 'test', version: '1.0.0', description: 'Test project' },
  modes: [
    { id: 'cup', label: 'Start', label_es: 'Inicio', scad_file: 'test.scad', parts: ['body'] },
    { id: 'single', label: 'Single', label_es: 'Individual', scad_file: 'test.scad', parts: ['body'] },
    { id: 'grid', label: 'Grid', label_es: 'Cuadrícula', scad_file: 'test.scad', parts: ['body', 'rod'] },
  ],
  parameters: [
    { id: 'width', type: 'slider', label: 'Width', label_es: 'Ancho', default: 50, min: 10, max: 200, step: 1, visible_in_modes: ['cup', 'single', 'grid'] },
    { id: 'height', type: 'slider', label: 'Height', label_es: 'Alto', default: 30, min: 5, max: 100, step: 1, visible_in_modes: ['cup', 'single', 'grid'] },
    { id: 'letter', type: 'text', label: 'Letter', label_es: 'Letra', default: 'A', maxlength: 1, visible_in_modes: ['cup', 'single'] },
    { id: 'show_base', type: 'checkbox', label: 'Show Base', label_es: 'Mostrar Base', default: true, visible_in_modes: ['cup', 'single', 'grid'] },
  ],
  presets: [
    { id: 'small', label: 'Small', label_es: 'Pequeño', values: { width: 30, height: 20 } },
    { id: 'large', label: 'Large', label_es: 'Grande', values: { width: 150, height: 80 } },
  ],
  parts: [
    { id: 'body', label: 'Body', label_es: 'Cuerpo', default_color: '#e5e7eb' },
    { id: 'rod', label: 'Rod', label_es: 'Barra', default_color: '#3b82f6' },
  ],
  camera_views: [
    { id: 'iso', label: 'Isometric', label_es: 'Isométrico', position: [50, 50, 50] },
    { id: 'top', label: 'Top', label_es: 'Superior', position: [0, 0, 100] },
    { id: 'front', label: 'Front', label_es: 'Frente', position: [0, 100, 0] },
    { id: 'right', label: 'Right', label_es: 'Derecha', position: [100, 0, 0] },
  ],
  viewer: { default_color: '#e5e7eb' },
  export_formats: ['stl', '3mf', 'off'],
  parameter_groups: [
    {
      id: 'visibility',
      label: 'Visibility',
      label_es: 'Visibilidad',
      levels: [
        { id: 'basic', label: 'Advanced', label_es: 'Avanzado' },
        { id: 'advanced', label: 'Basic', label_es: 'Básico' },
      ],
    },
    { id: 'colors', label: 'Colors', label_es: 'Colores' },
  ],
  estimate_constants: { base_time: 5, time_per_mm3: 0.001 },
}

const MOCK_PROJECTS = [
  { slug: 'test', name: 'Test Project', version: '1.0.0', description: 'A test', mode_count: 2, parameter_count: 4, scad_file_count: 1, has_manifest: true, has_exports: false },
  { slug: 'demo', name: 'Demo Project', version: '0.1.0', description: 'A demo', mode_count: 1, parameter_count: 2, scad_file_count: 1, has_manifest: true, has_exports: true },
]

// Minimal valid binary STL (134 bytes, 1 triangle)
function createMinimalSTL() {
  // 80-byte header + 4-byte count + 50-byte triangle = 134 bytes
  const buffer = new ArrayBuffer(134)
  const view = new DataView(buffer)
  view.setUint32(80, 1, true) // 1 triangle
  // Triangle: normal(0,0,1) + 3 vertices forming a small triangle + 2-byte attribute
  const off = 84
  view.setFloat32(off + 0, 0, true)  // normal x
  view.setFloat32(off + 4, 0, true)  // normal y
  view.setFloat32(off + 8, 1, true)  // normal z
  view.setFloat32(off + 12, 0, true) // v1 x
  view.setFloat32(off + 16, 0, true) // v1 y
  view.setFloat32(off + 20, 0, true) // v1 z
  view.setFloat32(off + 24, 1, true) // v2 x
  view.setFloat32(off + 28, 0, true) // v2 y
  view.setFloat32(off + 32, 0, true) // v2 z
  view.setFloat32(off + 36, 0, true) // v3 x
  view.setFloat32(off + 40, 1, true) // v3 y
  view.setFloat32(off + 44, 0, true) // v3 z
  view.setUint16(off + 48, 0, true)  // attribute byte count
  return Buffer.from(buffer)
}

/**
 * Mock all API routes with deterministic responses.
 * @param {import('@playwright/test').Page} page
 */
export async function mockAllAPIs(page) {
  await page.route('**/api/projects', (route) => {
    if (route.request().url().includes('/api/projects/')) return route.fallback()
    console.log('MOCK: Intercepted GET /api/projects')
    route.fulfill({ json: MOCK_PROJECTS })
  })

  await page.route('**/api/projects/*/manifest', (route) => {
    console.log('MOCK: Intercepted GET manifest', route.request().url())
    route.fulfill({ json: MOCK_MANIFEST })
  })

  await page.route('**/api/manifest', (route) => {
    console.log('MOCK: Intercepted GET /api/manifest')
    route.fulfill({ json: MOCK_MANIFEST })
  })

  await page.route('**/api/health', (route) => {
    route.fulfill({ json: { status: 'ok', openscad: true } })
  })

  await page.route('**/api/render', (route) => {
    route.fulfill({
      contentType: 'model/stl',
      body: createMinimalSTL(),
    })
  })

  await page.route('**/api/render-stream', (route) => {
    const body = [
      'data: {"event":"part_start","part":"body","index":0,"total":1}\n\n',
      'data: {"progress":50}\n\n',
      'data: {"event":"part_done","part":"body","progress":100}\n\n',
      'data: {"event":"complete","parts":[{"type":"body","url":"/api/render/body.stl"}]}\n\n',
    ].join('')
    route.fulfill({
      contentType: 'text/event-stream',
      body,
    })
  })

  await page.route(/\/api\/render\/.*\.stl/, (route) => {
    route.fulfill({
      contentType: 'model/stl',
      body: createMinimalSTL(),
    })
  })

  await page.route('**/api/estimate', (route) => {
    route.fulfill({ json: { estimated_time: 5 } })
  })

  await page.route('**/api/verify', (route) => {
    route.fulfill({ json: { passed: true, checks: [] } })
  })

  await page.route('**/api/admin/projects**', (route) => {
    route.fulfill({ json: MOCK_PROJECTS })
  })
}

/**
 * Mock API to return error responses.
 */
export async function mockAPIErrors(page) {
  await page.route('**/api/render', (route) => {
    route.fulfill({ status: 500, json: { error: 'Render failed' } })
  })

  await page.route('**/api/manifest', (route) => {
    route.fulfill({ status: 500, json: { error: 'Server error' } })
  })

  await page.route('**/api/admin/projects**', (route) => {
    route.fulfill({ status: 500, json: { error: 'Server error' } })
  })
}

/**
 * Mock API with network timeouts.
 */
export async function mockAPITimeout(page) {
  await page.route('**/api/render', (route) => {
    // Never fulfill — simulates timeout
    route.abort('timedout')
  })
}

export { MOCK_MANIFEST, MOCK_PROJECTS }
