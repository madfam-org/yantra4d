/* global Buffer */
import { test, expect } from '../../fixtures/app.fixture.js'
import { forceBackendRender, goToStudio, setLanguage } from '../../helpers/test-utils.js'

/**
 * The writable graph editor, end to end against mocked API routes:
 * open a graph cartridge (a fork), add nodes from the palette, connect them by
 * dragging between sockets, set a parameter, bind one to a manifest parameter,
 * watch the live validation turn valid, and export the .graph.json.
 *
 * The fork matters: the editor only ever writes a project whose
 * project.meta.json says `source.type: "fork"`, so /meta answers that, and the
 * save path's two writes (the graph, then the bindings) are captured here.
 */

const GRAPH = {
  version: '1.0.0',
  units: 'mm',
  nodes: [{ id: 'base', type: 'box', params: { w: 40, d: 20, h: 8 } }],
  outputs: { body: 'base' },
}

async function mockGraphCartridge(page) {
  const writes = { files: [], bindings: [] }
  let stored = `${JSON.stringify(GRAPH, null, 2)}\n`

  await page.route('**/api/projects/test/meta', (route) =>
    route.fulfill({ json: { source: { type: 'fork', forked_from: 'demo' } } }))
  await page.route('**/api/projects/test/files', (route) =>
    route.fulfill({ json: [{ path: 'part.graph.json', name: 'part.graph.json', size: stored.length }] }))
  await page.route('**/api/projects/test/files/part.graph.json', async (route) => {
    if (route.request().method() === 'PUT') {
      const { content } = route.request().postDataJSON()
      writes.files.push(JSON.parse(content))
      stored = content
      return route.fulfill({ json: { path: 'part.graph.json', size: content.length } })
    }
    return route.fulfill({ json: { path: 'part.graph.json', content: stored, size: stored.length } })
  })
  await page.route('**/api/projects/test/manifest/bindings', (route) => {
    const body = route.request().postDataJSON()
    writes.bindings.push(body)
    const bindings = Object.fromEntries(Object.entries(body.bindings).filter(([, v]) => v !== null))
    return route.fulfill({ json: { bindings } })
  })
  return writes
}

/** Drag from one node's output handle to another node's input socket. */
async function connect(page, source, target, socket) {
  await page.locator('.react-flow__controls-fitview').click()
  const from = page.locator(`.react-flow__handle[data-nodeid="${source}"][data-handleid="out"]`)
  const to = page.locator(`.react-flow__handle[data-nodeid="${target}"][data-handleid="${socket}"]`)
  await from.dragTo(to)
}

test.describe('Graph editor', () => {
  test.beforeEach(async ({ page }) => {
    await setLanguage(page, 'en')
    await page.addInitScript(() => sessionStorage.setItem('yantra4d-editor-open', 'true'))
    await forceBackendRender(page)
  })

  test('add, connect, set a parameter, bind, validate and export', async ({ page }) => {
    const writes = await mockGraphCartridge(page)
    await goToStudio(page)

    await page.getByRole('listbox', { name: 'Project files' }).getByText('part.graph.json', { exact: true }).click()
    await page.getByRole('button', { name: 'Graph', exact: true }).click()
    const editor = page.getByTestId('graph-editor')
    await expect(editor).toBeVisible()
    await expect(page.getByTestId('graph-node-base')).toBeVisible()

    // Palette: a cylinder and a cut.
    await editor.getByRole('button', { name: 'Nodes', exact: true }).click()
    await page.getByTestId('graph-palette-cylinder').click()
    await page.getByTestId('graph-palette-cut').click()
    await expect(page.getByTestId('graph-node-cut_1')).toBeVisible()
    // A cut with nothing connected is invalid, and says where.
    await expect(page.getByText('cut_1.a:')).toBeVisible()
    // Give the canvas the room: close the palette.
    await editor.getByRole('button', { name: 'Nodes', exact: true }).click()

    // Drag-to-connect. A profile could not go here; two solids can.
    await connect(page, 'base', 'cut_1', 'a')
    await connect(page, 'cylinder_1', 'cut_1', 'b')
    await expect(page.locator('.react-flow__edge[data-id="cylinder_1->cut_1.b"]')).toHaveCount(1)
    await expect(page.locator('.react-flow__edge[data-id="base->cut_1.a"]')).toHaveCount(1)

    // Make the cut the part, through the inspector.
    await page.getByTestId('graph-node-cut_1').click()
    const part = page.getByLabel('Part id')
    await part.fill('body')
    await part.press('Enter')
    await expect(page.getByText(/^Valid · 3 nodes · 1 part$/)).toBeVisible()

    // Set a parameter: the cylinder's radius.
    await page.getByTestId('graph-node-cylinder_1').click()
    await page.getByLabel('Value of r').fill('4')
    await expect.poll(() => writes.files.at(-1)?.nodes.find((n) => n.id === 'cylinder_1')?.params.r).toBe(4)

    // Bind the cylinder's height to the manifest's "height" slider.
    await page.getByLabel('How h is set').selectOption('bound')
    await page.getByLabel('Manifest parameter driving h').selectOption('height')
    await expect.poll(() => writes.bindings.at(-1)).toEqual({ bindings: { height: 'cylinder_1.h' } })
    // The graph is always written before the bindings that point into it.
    const saved = writes.files.at(-1)
    expect(saved.nodes.map((n) => n.id)).toEqual(['base', 'cylinder_1', 'cut_1'])
    expect(saved.outputs).toEqual({ body: 'cut_1' })

    // Export what is on screen.
    const download = page.waitForEvent('download')
    await editor.getByRole('button', { name: 'Export .graph.json' }).click()
    const file = await download
    expect(file.suggestedFilename()).toBe('part.graph.json')
    const stream = await file.createReadStream()
    const chunks = []
    for await (const chunk of stream) chunks.push(chunk)
    const exported = JSON.parse(Buffer.concat(chunks).toString('utf8'))
    expect(exported.nodes.find((n) => n.id === 'cut_1').inputs).toEqual({ a: 'base', b: 'cylinder_1' })
    expect(exported.nodes.find((n) => n.id === 'cylinder_1').params.r).toBe(4)
  })

  test('a commons cartridge is edited in place but never written', async ({ page }) => {
    const writes = await mockGraphCartridge(page)
    await page.unroute('**/api/projects/test/meta')
    await page.route('**/api/projects/test/meta', (route) => route.fulfill({ status: 404, json: { error: 'No meta' } }))
    await goToStudio(page)

    await page.getByRole('listbox', { name: 'Project files' }).getByText('part.graph.json', { exact: true }).click()
    await page.getByRole('button', { name: 'Graph', exact: true }).click()
    await expect(page.getByTestId('graph-save-status')).toHaveText(/Commons cartridge/)
    await expect(page.getByRole('button', { name: 'Fork to save' })).toBeVisible()

    await page.getByRole('button', { name: 'Nodes', exact: true }).click()
    await page.getByTestId('graph-palette-sphere').click()
    await expect(page.getByTestId('graph-node-sphere_1')).toBeVisible()
    // Past the save debounce: nothing was written.
    await page.waitForTimeout(1500)
    expect(writes.files).toEqual([])
    expect(writes.bindings).toEqual([])
  })
})
