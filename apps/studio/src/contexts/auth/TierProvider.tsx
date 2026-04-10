import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getApiBase } from '../../services/core/backendDetection'
import { useAuth, isAuthEnabled } from './AuthProvider'
import { apiFetch } from '../../services/core/apiClient'

type TierName = 'guest' | 'essentials' | 'basic' | 'pro' | 'madfam'

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

const TIER_HIERARCHY: Record<string, number> = { guest: 0, essentials: 1, basic: 1, pro: 2, madfam: 3 }

const FALLBACK: TierContextValue = {
  tier: isAuthEnabled ? 'guest' : 'madfam',
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

  const tier = userInfo?.tier || (isAuthEnabled ? 'guest' : 'madfam')
  const limits = userInfo?.limits || (allTiers ? allTiers[tier] : null) as Record<string, unknown> | null

  const canAccess = useCallback((requiredTier: string) => {
    if (!isAuthEnabled) return true
    return (TIER_HIERARCHY[tier] ?? 0) >= (TIER_HIERARCHY[requiredTier] ?? 0)
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
