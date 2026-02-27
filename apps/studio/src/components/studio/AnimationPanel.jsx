/**
 * AnimationPanel.jsx
 *
 * Studio sidebar panel that lists parametric animation sequences defined in
 * the project manifest's `animations[]` array. Users can trigger a server-side
 * flipbook render and play back the resulting GLB frames in the 3D viewport.
 *
 * Props:
 *   projectSlug  : string — current project identifier
 *   manifest     : object — parsed project.json data
 *   onLoadFrame  : (glbUrls: string[]) => void — called with frame GLB URLs for the viewport
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import './AnimationPanel.css'

/** Retrieve available animations from the backend (mirrors manifest data). */
async function fetchAnimations(slug) {
    const res = await fetch(`/api/projects/${slug}/animations`)
    if (!res.ok) return []
    const data = await res.json()
    return data.animations ?? []
}

/** Parse an SSE stream and call onEvent for each parsed data line. */
function consumeSSE(response, onEvent, signal) {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    async function pump() {
        while (true) {
            if (signal?.aborted) break
            const { done, value } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() ?? ''
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const event = JSON.parse(line.slice(6))
                        onEvent(event)
                    } catch { /* ignore malformed SSE event */ }
                }
            }
        }
    }
    return pump()
}

export default function AnimationPanel({ projectSlug, onLoadFrame }) {
    const [animations, setAnimations] = useState([])
    const [selectedId, setSelectedId] = useState(null)
    const [status, setStatus] = useState('idle') // idle | rendering | playing | error
    const [progress, setProgress] = useState(0)
    const [frames, setFrames] = useState([]) // [{frame_index, parts: [{url}]}]
    const [currentFrame, setCurrentFrame] = useState(0)
    const [error, setError] = useState(null)
    const abortRef = useRef(null)
    const playTimerRef = useRef(null)

    // Load animation list
    useEffect(() => {
        if (!projectSlug) return
        fetchAnimations(projectSlug).then(setAnimations)
    }, [projectSlug])

    const selectedAnim = animations.find(a => a.id === selectedId)

    // ── Render ──────────────────────────────────────────────────────────────────
    const handleRender = useCallback(async () => {
        if (!selectedId || status === 'rendering') return
        setStatus('rendering')
        setProgress(0)
        setFrames([])
        setCurrentFrame(0)
        setError(null)

        const controller = new AbortController()
        abortRef.current = controller

        try {
            const res = await fetch(
                `/api/projects/${projectSlug}/animations/${selectedId}/render`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ parameters: {} }),
                    signal: controller.signal,
                }
            )

            if (!res.ok) {
                const err = await res.json()
                throw new Error(err.error ?? `HTTP ${res.status}`)
            }

            const collectedFrames = []

            await consumeSSE(res, event => {
                if (event.event === 'frame_done') {
                    setProgress(event.progress)
                } else if (event.event === 'complete') {
                    collectedFrames.push(...(event.frames ?? []))
                    setFrames([...collectedFrames])
                    setStatus('playing')
                    setProgress(100)
                } else if (event.event === 'error') {
                    throw new Error(event.error ?? 'Render error')
                }
            }, controller.signal)
        } catch (err) {
            if (err.name === 'AbortError') {
                setStatus('idle')
            } else {
                setError(err.message)
                setStatus('error')
            }
        }
    }, [selectedId, projectSlug, status])

    const handleCancel = useCallback(() => {
        abortRef.current?.abort()
        clearInterval(playTimerRef.current)
        setStatus('idle')
    }, [])

    // ── Playback ─────────────────────────────────────────────────────────────────
    useEffect(() => {
        if (status !== 'playing' || frames.length === 0) return
        const duration = selectedAnim?.duration_ms ?? 2000
        const interval = duration / frames.length

        clearInterval(playTimerRef.current)
        playTimerRef.current = setInterval(() => {
            setCurrentFrame(prev => {
                const next = (prev + 1) % frames.length
                const frameGlbs = frames[next]?.parts?.map(p => p.url) ?? []
                if (onLoadFrame && frameGlbs.length) onLoadFrame(frameGlbs)
                return next
            })
        }, interval)

        return () => clearInterval(playTimerRef.current)
    }, [status, frames, selectedAnim, onLoadFrame])

    // Load first frame into viewport when frames arrive
    useEffect(() => {
        if (frames.length > 0 && onLoadFrame) {
            const firstGlbs = frames[0]?.parts?.map(p => p.url) ?? []
            if (firstGlbs.length) onLoadFrame(firstGlbs)
        }
    }, [frames]) // eslint-disable-line react-hooks/exhaustive-deps

    if (animations.length === 0) return null

    return (
        <div className="animation-panel" role="region" aria-label="Animation Panel">
            <h3 className="animation-panel__title">
                <span className="animation-panel__icon">▶</span>
                Animations
            </h3>

            {/* Animation cards */}
            <div className="animation-panel__list">
                {animations.map(anim => {
                    const label = typeof anim.label === 'object' ? (anim.label.en ?? anim.id) : anim.label
                    const desc = anim.description
                        ? (typeof anim.description === 'object' ? anim.description.en : anim.description)
                        : null
                    const isSelected = anim.id === selectedId
                    return (
                        <button
                            key={anim.id}
                            className={`animation-panel__card ${isSelected ? 'animation-panel__card--active' : ''}`}
                            onClick={() => setSelectedId(anim.id)}
                            disabled={status === 'rendering'}
                        >
                            <span className="animation-panel__card-label">{label}</span>
                            {desc && <span className="animation-panel__card-desc">{desc}</span>}
                            <span className="animation-panel__card-meta">
                                {anim.frames} frames · {anim.duration_ms}ms · {anim.easing ?? 'ease-in-out'}
                            </span>
                        </button>
                    )
                })}
            </div>

            {/* Controls */}
            {selectedId && (
                <div className="animation-panel__controls">
                    {status === 'idle' || status === 'error' ? (
                        <button
                            className="animation-panel__btn animation-panel__btn--primary"
                            onClick={handleRender}
                            id="anim-render-btn"
                        >
                            Render Animation
                        </button>
                    ) : status === 'rendering' ? (
                        <>
                            <div className="animation-panel__progress-bar">
                                <div
                                    className="animation-panel__progress-fill"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                            <span className="animation-panel__progress-label">{progress.toFixed(0)}%</span>
                            <button
                                className="animation-panel__btn animation-panel__btn--cancel"
                                onClick={handleCancel}
                            >
                                Cancel
                            </button>
                        </>
                    ) : (
                        /* Playing */
                        <div className="animation-panel__playback">
                            <span className="animation-panel__frame-label">
                                Frame {currentFrame + 1} / {frames.length}
                            </span>
                            <div className="animation-panel__scrub">
                                <input
                                    type="range"
                                    min={0}
                                    max={frames.length - 1}
                                    value={currentFrame}
                                    onChange={e => {
                                        const f = Number(e.target.value)
                                        setCurrentFrame(f)
                                        const glbs = frames[f]?.parts?.map(p => p.url) ?? []
                                        if (onLoadFrame && glbs.length) onLoadFrame(glbs)
                                    }}
                                    aria-label="Animation frame scrubber"
                                />
                            </div>
                            <button
                                className="animation-panel__btn animation-panel__btn--secondary"
                                onClick={() => {
                                    setStatus('idle')
                                    setFrames([])
                                    setCurrentFrame(0)
                                    clearInterval(playTimerRef.current)
                                }}
                            >
                                Reset
                            </button>
                        </div>
                    )}
                    {error && (
                        <p className="animation-panel__error" role="alert">{error}</p>
                    )}
                </div>
            )}
        </div>
    )
}
