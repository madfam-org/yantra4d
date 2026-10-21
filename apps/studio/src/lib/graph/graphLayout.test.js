import { describe, it, expect } from 'vitest'
import { COLUMN_WIDTH, ROW_HEIGHT, layoutNodes, nextFreePosition } from './graphLayout'

const chain = [
  { id: 'base', type: 'box' },
  { id: 'bore', type: 'cylinder' },
  { id: 'body', type: 'cut', inputs: { a: 'base', b: 'bore' } },
]

describe('layoutNodes', () => {
  it('places sources in the first column and consumers to their right', () => {
    const placed = layoutNodes(chain)
    expect(placed.get('base')).toEqual({ x: 0, y: 0 })
    expect(placed.get('bore')).toEqual({ x: 0, y: ROW_HEIGHT })
    expect(placed.get('body')).toEqual({ x: COLUMN_WIDTH, y: 0 })
  })

  it('keeps a position the author stored in meta', () => {
    const nodes = structuredClone(chain)
    nodes[2].meta = { position: { x: 900, y: -40 } }
    expect(layoutNodes(nodes).get('body')).toEqual({ x: 900, y: -40 })
  })

  it('ignores a malformed stored position', () => {
    const nodes = structuredClone(chain)
    nodes[0].meta = { position: { x: 'left', y: 3 } }
    nodes[1].meta = { position: { x: Infinity, y: 3 } }
    expect(layoutNodes(nodes).get('base')).toEqual({ x: 0, y: 0 })
    expect(layoutNodes(nodes).get('bore')).toEqual({ x: 0, y: ROW_HEIGHT })
  })

  it('still draws a graph with a loop, so the author can see it to break it', () => {
    const loop = [
      { id: 'a', type: 'translate', inputs: { shape: 'b' } },
      { id: 'b', type: 'translate', inputs: { shape: 'a' } },
    ]
    const placed = layoutNodes(loop)
    expect(placed.size).toBe(2)
    expect(placed.get('a')).not.toEqual(placed.get('b'))
  })
})

describe('nextFreePosition', () => {
  it('starts at the origin on an empty canvas', () => {
    expect(nextFreePosition([])).toEqual({ x: 0, y: 0 })
  })

  it('goes one row below the lowest node', () => {
    expect(nextFreePosition([{ x: 0, y: 0 }, { x: 400, y: 240 }])).toEqual({ x: 0, y: 240 + ROW_HEIGHT })
  })
})
