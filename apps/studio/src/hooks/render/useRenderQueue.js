import { useState, useCallback, useRef } from 'react'

/**
 * Simple in-memory render queue for batch rendering.
 * Processes items sequentially, provides queue status and cancel per item.
 */
export function useRenderQueue({ renderFn }) {
  const [queue, setQueue] = useState([])
  const queueRef = useRef([])
  const [currentId, setCurrentId] = useState(null)
  const processingRef = useRef(false)
  const cancelledRef = useRef(new Set())

  const syncQueue = (newQueue) => {
    queueRef.current = newQueue
    setQueue(newQueue)
  }

  const enqueue = useCallback((item) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
    const entry = { id, ...item, status: 'pending', result: null }
    syncQueue([...queueRef.current, entry])
    return id
  }, [])

  const cancelItem = useCallback((id) => {
    cancelledRef.current.add(id)
    syncQueue(queueRef.current.map(item =>
      item.id === id ? { ...item, status: 'cancelled' } : item
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
        item.id === nextItem.id ? { ...item, status: 'processing' } : item
      ))

      try {
        const result = await renderFn(nextItem)
        if (!cancelledRef.current.has(nextItem.id)) {
          syncQueue(queueRef.current.map(item =>
            item.id === nextItem.id ? { ...item, status: 'completed', result } : item
          ))
        }
      } catch (err) {
        syncQueue(queueRef.current.map(item =>
          item.id === nextItem.id ? { ...item, status: 'failed', error: err.message } : item
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
