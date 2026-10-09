/**
 * Studio-side state for the viewer's render quality: the user's mode
 * (persisted), the render scale the canvas applies and the readings shown in
 * the View panel. The controller itself is the self-contained ./renderBudget.
 */
import { useSyncExternalStore } from 'react'
import { QUALITY_MODES, type QualityMode, type RenderBudgetStats } from './renderBudget'

export { MAX_DPR, QUALITY_MODES } from './renderBudget'
export type { QualityMode } from './renderBudget'
export type QualityReadings = RenderBudgetStats

const STORAGE_KEY = 'yantra4d-viewer-quality'
const EMPTY_READINGS: QualityReadings = {
  gpu: null, browser: '', timerQuery: false, scale: 1,
  gpuMsP50: null, gpuMsP90: null, fps: 0, drawCalls: 0, triangles: 0,
}

function isQualityMode(value: unknown): value is QualityMode {
  return QUALITY_MODES.includes(value as QualityMode)
}

function readStoredMode(): QualityMode {
  try {
    const stored = globalThis.localStorage?.getItem(STORAGE_KEY)
    return isQualityMode(stored) ? stored : 'auto'
  } catch {
    return 'auto'
  }
}

interface QualityState {
  mode: QualityMode
  renderScale: number
  readings: QualityReadings
}

let state: QualityState = { mode: readStoredMode(), renderScale: 1, readings: EMPTY_READINGS }
const listeners = new Set<() => void>()

function update(patch: Partial<QualityState>): void {
  state = { ...state, ...patch }
  listeners.forEach((listener) => listener())
}

export function subscribeQuality(listener: () => void): () => void {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export const getQualityMode = (): QualityMode => state.mode
export const getRenderScale = (): number => state.renderScale
export const getQualityReadings = (): QualityReadings => state.readings

export function setQualityMode(mode: QualityMode): void {
  if (!isQualityMode(mode) || mode === state.mode) return
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, mode)
  } catch {
    // Storage unavailable (private window, blocked site data): the choice
    // still applies for this session.
  }
  update({ mode })
}

export function setRenderScale(renderScale: number): void {
  if (renderScale !== state.renderScale) update({ renderScale })
}

export function publishReadings(readings: QualityReadings): void {
  const prev = state.readings
  const same = (Object.keys(readings) as (keyof QualityReadings)[]).every((key) => prev[key] === readings[key])
  if (!same) update({ readings })
}

export const useQualityMode = (): QualityMode => useSyncExternalStore(subscribeQuality, getQualityMode)
export const useRenderScale = (): number => useSyncExternalStore(subscribeQuality, getRenderScale)
export const useQualityReadings = (): QualityReadings => useSyncExternalStore(subscribeQuality, getQualityReadings)
