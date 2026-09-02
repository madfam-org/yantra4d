import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getApiBase } from '../../services/core/backendDetection'
import { useAuth, isAuthEnabled } from './AuthProvider'
import { apiFetch } from '../../services/core/apiClient'
import { TOP_TIER, tierAtLeast } from '../../lib/tiers'

interface TierConfig {
  [key: string]: unknown
}

interface UserInfo {
  tier?: string
  limits?: Record<string, unknown> | null
  [key: string]: unknown
}

export interface TierContextValue {
  tier: string
  tierConfig: TierConfig | null
  limits: Record<string, unknown> | null
  allTiers: Record<string, TierConfig> | null
  loading: boolean
  canAccess: (requiredTier: string) => boolean
}

interface TierProviderProps {
  children: React.ReactNode
}

export const TierContext = createContext<TierContextValue | null>(null)

const FALLBACK: TierContextValue = {
  tier: isAuthEnabled ? 'guest' : TOP_TIER,
  tierConfig: null,
  limits: null,
  allTiers: null,
  loading: true,
  canAccess: () => !isAuthEnabled,
}

export function TierProvider({ children }: TierProviderProps) {
  const { isAuthenticated } = useAuth()
  const [allTiers, setAllTiers] = useState<Record<string, TierConfig> | null>(null)
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)

  // Fetch tier definitions once
  useEffect(() => {
    apiFetch(`${getApiBase()}/api/tiers`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setAllTiers(data) })
      .catch(() => { })
  }, [])

  // Fetch current user tier whenever auth state changes
  useEffect(() => {
    let cancelled = false
    apiFetch(`${getApiBase()}/api/me`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!cancelled) {
          if (data) setUserInfo(data)
          setLoading(false)
        }
      })
      .catch(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [isAuthenticated])

  const tier = userInfo?.tier || (isAuthEnabled ? 'guest' : TOP_TIER)
  const limits = userInfo?.limits || (allTiers ? allTiers[tier] : null) as Record<string, unknown> | null

  // `tierAtLeast` normalises deprecated names on both sides, so a cached
  // /api/me still saying `madfam` grants exactly what `premium` grants.
  const canAccess = useCallback((requiredTier: string) => {
    if (!isAuthEnabled) return true
    return tierAtLeast(tier, requiredTier)
  }, [tier])

  const value: TierContextValue = {
    tier,
    tierConfig: (allTiers?.[tier] || null) as TierConfig | null,
    limits,
    allTiers,
    loading,
    canAccess,
  }

  return (
    <TierContext.Provider value={value}>
      {children}
    </TierContext.Provider>
  )
}

export function useTier(): TierContextValue {
  return useContext(TierContext) || FALLBACK
}
