import { useState, useEffect, useRef } from 'react'

/**
 * Dynamic plugin loader for custom parameter widgets.
 * Loads ES modules from URLs specified in manifest parameter `widget` config.
 * Plugin interface: { value, onChange, param } → React element
 *
 * Security: Only loads from same-origin or allowlisted domains.
 */
export default function PluginLoader({ url, value, onChange, param }) {
  const [Component, setComponent] = useState(null)
  const [error, setError] = useState(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  useEffect(() => {
    if (!url) return

    // Basic URL validation — same-origin or allowlisted
    try {
      const parsed = new URL(url, window.location.origin)
      const allowedOrigins = [window.location.origin]
      if (!allowedOrigins.includes(parsed.origin)) {
        setError(`Plugin origin not allowed: ${parsed.origin}`)
        return
      }
    } catch {
      setError(`Invalid plugin URL: ${url}`)
      return
    }

    import(/* @vite-ignore */ url)
      .then(mod => {
        if (mountedRef.current) {
          setComponent(() => mod.default || mod.Widget)
        }
      })
      .catch(err => {
        if (mountedRef.current) {
          setError(`Failed to load plugin: ${err.message}`)
        }
      })
  }, [url])

  if (error) {
    return <div className="text-xs text-destructive">{error}</div>
  }

  if (!Component) {
    return <div className="text-xs text-muted-foreground">Loading plugin…</div>
  }

  return <Component value={value} onChange={onChange} param={param} />
}
