/**
 * Where each node is drawn.
 *
 * A node the author has moved carries its position in `meta.position`. Every
 * other node is laid out left to right by dependency depth — sources first,
 * the finished part last, which is how these graphs read. A graph with a loop
 * has no depth, so it falls back to a grid rather than drawing nothing: the
 * author needs to see the loop to break it.
 */
import { dependencyDepth, nodePosition } from './graphDocument'
import type { GraphNode, NodePosition } from './graphDocument'

export const COLUMN_WIDTH = 230
export const ROW_HEIGHT = 120

export function layoutNodes(nodes: GraphNode[]): Map<string, NodePosition> {
  const placed = new Map<string, NodePosition>()
  const depth = dependencyDepth(nodes)
  const perColumn = new Map<number, number>()

  nodes.forEach((node, index) => {
    const stored = nodePosition(node)
    if (stored) {
      placed.set(node.id, stored)
      return
    }
    const column = depth ? (depth.get(node.id) ?? 0) : index % 4
    const row = perColumn.get(column) ?? 0
    perColumn.set(column, row + 1)
    placed.set(node.id, { x: column * COLUMN_WIDTH, y: row * ROW_HEIGHT })
  })
  return placed
}

/** A free spot for a new node: below everything already in the first column it fits. */
export function nextFreePosition(positions: Iterable<NodePosition>): NodePosition {
  let maxY = -ROW_HEIGHT
  let any = false
  for (const pos of positions) {
    any = true
    if (pos.y > maxY) maxY = pos.y
  }
  return any ? { x: 0, y: maxY + ROW_HEIGHT } : { x: 0, y: 0 }
}
