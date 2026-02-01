import { useState, useCallback, useRef } from 'react'

/**
 * Simple in-memory render queue for batch rendering.
 * Processes items sequentially, provides queue status and cancel per item.
 */
export function useRenderQueue({ renderFn }) {
  const [queue, setQueue] = useState([])
  const [currentId, setCurrentId] = useState(null)
  const processingRef = useRef(false)
  const cancelledRef = useRef(new Set())

  const enqueue = useCallback((item) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
    const entry = { id, ...item, status: 'pending', result: null }
    setQueue(prev => [...prev, entry])
    return id
  }, [])

  const cancelItem = useCallback((id) => {
    cancelledRef.current.add(id)
    setQueue(prev => prev.map(item =>
      item.id === id ? { ...item, status: 'cancelled' } : item
    ))
  }, [])

  const clearCompleted = useCallback(() => {
    setQueue(prev => prev.filter(item => item.status === 'pending' || item.status === 'processing'))
  }, [])

  const processQueue = useCallback(async () => {
    if (processingRef.current) return
    processingRef.current = true

    setQueue(prev => {
      const next = prev.find(item => item.status === 'pending')
      if (next) {
        setCurrentId(next.id)
        return prev.map(item =>
          item.id === next.id ? { ...item, status: 'processing' } : item
        )
      }
      return prev
    })

    // Process pending items one by one
    while (true) {
      let nextItem = null
      setQueue(prev => {
        nextItem = prev.find(item => item.status === 'pending')
        if (nextItem) {
          setCurrentId(nextItem.id)
          return prev.map(item =>
            item.id === nextItem.id ? { ...item, status: 'processing' } : item
          )
        }
        return prev
      })

      if (!nextItem) break
      if (cancelledRef.current.has(nextItem.id)) continue

      try {
        const result = await renderFn(nextItem)
        if (!cancelledRef.current.has(nextItem.id)) {
          setQueue(prev => prev.map(item =>
            item.id === nextItem.id ? { ...item, status: 'completed', result } : item
          ))
        }
      } catch (err) {
        setQueue(prev => prev.map(item =>
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
