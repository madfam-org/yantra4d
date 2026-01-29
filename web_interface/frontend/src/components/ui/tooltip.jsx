import React, { useState, useRef } from 'react'

export function Tooltip({ content, children }) {
  const [open, setOpen] = useState(false)
  const timeout = useRef(null)

  const show = () => {
    timeout.current = setTimeout(() => setOpen(true), 200)
  }
  const hide = () => {
    clearTimeout(timeout.current)
    setOpen(false)
  }

  if (!content) return children

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {open && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-50 px-2 py-1 rounded bg-popover text-popover-foreground text-xs shadow-md border border-border whitespace-nowrap pointer-events-none">
          {content}
        </span>
      )}
    </span>
  )
}
