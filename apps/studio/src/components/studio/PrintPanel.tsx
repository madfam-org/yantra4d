/**
 * PrintPanel.tsx
 *
 * Studio sidebar panel for OctoPrint / Moonraker (Klipper/Mainsail) integration.
 * Fetches configured printers from `/api/printers`, displays live status with
 * animated temperature gauges, and provides a "Send to Printer" dispatch button
 * (tier-gated at pro+).
 *
 * Props:
 *   projectSlug      : string  — active project slug
 *   currentPartUrls  : string[] — GLB URLs of the current rendered parts to print
 *   tier             : string  — current user tier ('guest'|'basic'|'pro'|'madfam')
 */

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { apiFetch } from '../../services/core/apiClient'
import './PrintPanel.css'

const POLL_INTERVAL_MS = 5000

interface Printer {
    id: string
    name: string
    model: string
}

interface TempData {
    actual: number | null
    target: number
}

interface JobData {
    file: string
    progress_pct: number | null
    time_remaining_s: number | null
}

interface PrinterStatus {
    state: string
    temperatures?: {
        tool0?: TempData
        bed?: TempData
    }
    job?: JobData
}

interface TempGaugeProps {
    label: string
    actual: number | null
    target: number
    maxTemp?: number
}

interface PrintPanelProps {
    currentPartUrls?: string[]
    tier?: string
    projectSlug?: string
}

async function fetchPrinters(): Promise<Printer[]> {
    try {
        const res = await apiFetch('/api/printers')
        if (!res.ok) return []
        const data = await res.json()
        return data.printers ?? []
    } catch {
        return []
    }
}

async function fetchStatus(printerId: string): Promise<PrinterStatus | null> {
    try {
        const res = await apiFetch(`/api/printers/${printerId}/status`)
        if (!res.ok) return null
        return await res.json()
    } catch {
        return null
    }
}

async function dispatchPrint(printerId: string, fileUrl: string) {
    const res = await apiFetch(`/api/printers/${printerId}/print`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: fileUrl }),
    })
    if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error ?? `HTTP ${res.status}`)
    }
    return await res.json()
}

async function cancelPrint(printerId: string) {
    const res = await apiFetch(`/api/printers/${printerId}/print`, { method: 'DELETE' })
    if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error ?? `HTTP ${res.status}`)
    }
}

function TempGauge({ label, actual, target, maxTemp = 300 }: TempGaugeProps) {
    const pct = Math.min((actual ?? 0) / maxTemp, 1)
    const isHot = (actual ?? 0) > 40
    return (
        <div className="print-panel__gauge">
            <div className="print-panel__gauge-bar">
                <div
                    className={`print-panel__gauge-fill ${isHot ? 'print-panel__gauge-fill--hot' : ''}`}
                    style={{ width: `${pct * 100}%` }}
                />
            </div>
            <span className="print-panel__gauge-label">
                {label}: <strong>{actual != null ? `${actual.toFixed(1)}°C` : '—'}</strong>
                {target > 0 && ` / ${target.toFixed(0)}°C`}
            </span>
        </div>
    )
}

export default function PrintPanel({ currentPartUrls = [], tier = 'guest' }: PrintPanelProps) {
    const [printers, setPrinters] = useState<Printer[]>([])
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const [status, setStatus] = useState<PrinterStatus | null>(null)  // printer status object
    const [dispatching, setDispatching] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState<string | null>(null)
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

    const canPrint = tier === 'pro' || tier === 'madfam'

    // Load printer list once
    useEffect(() => {
        fetchPrinters().then(list => {
            setPrinters(list)
            if (list.length > 0 && !selectedId) setSelectedId(list[0].id)
        })
    }, []) // eslint-disable-line react-hooks/exhaustive-deps

    // Poll status for selected printer
    useEffect(() => {
        if (pollRef.current) clearInterval(pollRef.current)
        if (!selectedId) return

        const poll = () => {
            fetchStatus(selectedId).then(s => {
                if (s) setStatus(s)
            })
        }
        poll()
        pollRef.current = setInterval(poll, POLL_INTERVAL_MS)
        return () => { if (pollRef.current) clearInterval(pollRef.current) }
    }, [selectedId])

    const handlePrint = useCallback(async () => {
        if (!selectedId || !canPrint || dispatching) return
        setDispatching(true)
        setError(null)
        setSuccess(null)

        // Use the first STL/GLB URL from current render
        const fileUrl = currentPartUrls[0]
        if (!fileUrl) {
            setError('No rendered file available. Render the model first.')
            setDispatching(false)
            return
        }

        try {
            await dispatchPrint(selectedId, fileUrl)
            setSuccess('Print job dispatched successfully.')
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : String(err))
        } finally {
            setDispatching(false)
        }
    }, [selectedId, canPrint, dispatching, currentPartUrls])

    const handleCancel = useCallback(async () => {
        if (!selectedId) return
        try {
            await cancelPrint(selectedId)
            setSuccess('Print job cancelled.')
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : String(err))
        }
    }, [selectedId])

    if (printers.length === 0) return null

    const isPrinting = status?.state === 'Printing'
    const tempTool = status?.temperatures?.tool0
    const tempBed = status?.temperatures?.bed
    const job = status?.job

    return (
        <div className="print-panel" role="region" aria-label="Print Panel">
            <h3 className="print-panel__title">
                <span className="print-panel__icon">🖨</span>
                Print
            </h3>

            {/* Printer selector */}
            {printers.length > 1 && (
                <select
                    className="print-panel__select"
                    value={selectedId ?? ''}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedId(e.target.value)}
                    aria-label="Select printer"
                >
                    {printers.map(p => (
                        <option key={p.id} value={p.id}>
                            {p.name} ({p.model})
                        </option>
                    ))}
                </select>
            )}

            {/* Status */}
            {status && (
                <div className="print-panel__status">
                    <span className={`print-panel__state print-panel__state--${status.state?.toLowerCase()}`}>
                        {status.state ?? 'Unknown'}
                    </span>

                    {/* Temperature gauges */}
                    {tempTool && (
                        <TempGauge
                            label="Nozzle"
                            actual={tempTool.actual}
                            target={tempTool.target}
                            maxTemp={300}
                        />
                    )}
                    {tempBed && (
                        <TempGauge
                            label="Bed"
                            actual={tempBed.actual}
                            target={tempBed.target}
                            maxTemp={120}
                        />
                    )}

                    {/* Job progress */}
                    {job && (
                        <div className="print-panel__job">
                            <span className="print-panel__job-file">{job.file}</span>
                            <div className="print-panel__progress-bar">
                                <div
                                    className="print-panel__progress-fill"
                                    style={{ width: `${job.progress_pct ?? 0}%` }}
                                />
                            </div>
                            <span className="print-panel__job-meta">
                                {job.progress_pct?.toFixed(1)}%
                                {job.time_remaining_s != null && ` · ${Math.round(job.time_remaining_s / 60)}min left`}
                            </span>
                        </div>
                    )}
                </div>
            )}

            {/* Actions */}
            <div className="print-panel__actions">
                {canPrint ? (
                    <>
                        {!isPrinting ? (
                            <button
                                className="print-panel__btn print-panel__btn--primary"
                                onClick={handlePrint}
                                disabled={dispatching || currentPartUrls.length === 0}
                                id="print-dispatch-btn"
                            >
                                {dispatching ? 'Sending…' : 'Send to Printer'}
                            </button>
                        ) : (
                            <button
                                className="print-panel__btn print-panel__btn--cancel"
                                onClick={handleCancel}
                                id="print-cancel-btn"
                            >
                                Cancel Print
                            </button>
                        )}
                    </>
                ) : (
                    <div className="print-panel__upgrade">
                        <span>🔒 Print dispatch requires</span>
                        <strong>Pro</strong> tier.
                    </div>
                )}
            </div>

            {error && <p className="print-panel__error" role="alert">{error}</p>}
            {success && <p className="print-panel__success" role="status">{success}</p>}
        </div>
    )
}
