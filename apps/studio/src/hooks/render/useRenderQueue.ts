import { useState, useCallback, useRef } from 'react'

type QueueItemStatus = 'pending' | 'processing' | 'completed' | 'cancelled' | 'failed'

interface QueueItem {
  id: string
  status: QueueItemStatus
  result: unknown
  error?: string
  [key: string]: unknown
}

interface RenderQueueOptions {
  renderFn: (item: QueueItem) => Promise<unknown>
}

interface RenderQueueResult {
  queue: QueueItem[]
  currentId: string | null
  enqueue: (item: Record<string, unknown>) => string
  cancelItem: (id: string) => void
  clearCompleted: () => void
  processQueue: () => Promise<void>
  isProcessing: boolean
  pendingCount: number
}

/**
 * Simple in-memory render queue for batch rendering.
 * Processes items sequentially, provides queue status and cancel per item.
 */
export function useRenderQueue({ renderFn }: RenderQueueOptions): RenderQueueResult {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const queueRef = useRef<QueueItem[]>([])
  const [currentId, setCurrentId] = useState<string | null>(null)
  const processingRef = useRef(false)
  const cancelledRef = useRef(new Set<string>())

  const syncQueue = (newQueue: QueueItem[]): void => {
    queueRef.current = newQueue
    setQueue(newQueue)
  }

  const enqueue = useCallback((item: Record<string, unknown>): string => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
    const entry: QueueItem = { id, ...item, status: 'pending', result: null }
    syncQueue([...queueRef.current, entry])
    return id
  }, [])

  const cancelItem = useCallback((id: string) => {
    cancelledRef.current.add(id)
    syncQueue(queueRef.current.map(item =>
      item.id === id ? { ...item, status: 'cancelled' as const } : item
    ))
  }, [])

  const clearCompleted = useCallback(() => {
    syncQueue(queueRef.current.filter(item => item.status === 'pending' || item.status === 'processing'))
  }, [])

  const processQueue = useCallback(async () => {
    if (processingRef.current) return
    processingRef.current = true

    // Process pending items one by one
    while (true) {
      const nextItem = queueRef.current.find(item => item.status === 'pending')

      if (!nextItem) break
      if (cancelledRef.current.has(nextItem.id)) {
        continue
      }

      setCurrentId(nextItem.id)
      syncQueue(queueRef.current.map(item =>
        item.id === nextItem.id ? { ...item, status: 'processing' as const } : item
      ))

      try {
        const result = await renderFn(nextItem)
        if (!cancelledRef.current.has(nextItem.id)) {
          syncQueue(queueRef.current.map(item =>
            item.id === nextItem.id ? { ...item, status: 'completed' as const, result } : item
          ))
        }
      } catch (err) {
        syncQueue(queueRef.current.map(item =>
          item.id === nextItem.id ? { ...item, status: 'failed' as const, error: (err as Error).message } : item
        ))
      }
    }

    setCurrentId(null)
    processingRef.current = false
  }, [renderFn])

  return {
    queue,
    currentId,
    enqueue,
    cancelItem,
    clearCompleted,
    processQueue,
    isProcessing: processingRef.current,
    pendingCount: queue.filter(q => q.status === 'pending').length,
  }
}
