import React, { useState, useRef, useId, useCallback } from 'react'

export function Tooltip({ content, children }) {
  const [open, setOpen] = useState(false)
  const timeout = useRef(null)
  const dismissTimeout = useRef(null)
  const tooltipId = useId()

  const show = () => {
    clearTimeout(dismissTimeout.current)
    timeout.current = setTimeout(() => setOpen(true), 200)
  }
  const hide = () => {
    clearTimeout(timeout.current)
    clearTimeout(dismissTimeout.current)
    setOpen(false)
  }

  const handlePointerDown = useCallback((e) => {
    if (e.pointerType === 'touch') {
      clearTimeout(timeout.current)
      clearTimeout(dismissTimeout.current)
      setOpen(prev => {
        if (!prev) {
          dismissTimeout.current = setTimeout(() => setOpen(false), 2000)
        }
        return !prev
      })
    }
  }, [])

  if (!content) return children

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      onPointerDown={handlePointerDown}
      aria-describedby={open ? tooltipId : undefined}
    >
      {children}
      {open && (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-50 px-2 py-1 rounded bg-popover text-popover-foreground text-sm shadow-md border border-border whitespace-nowrap pointer-events-none"
        >
          {content}
        </span>
      )}
    </span>
  )
}
