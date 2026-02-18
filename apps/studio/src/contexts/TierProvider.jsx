import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getApiBase } from '../services/backendDetection'
import { useAuth, isAuthEnabled } from './AuthProvider'
import { apiFetch } from '../services/apiClient'

// eslint-disable-next-line react-refresh/only-export-components
export const TierContext = createContext(null)

const TIER_HIERARCHY = { guest: 0, basic: 1, pro: 2, madfam: 3 }

const FALLBACK = {
  tier: isAuthEnabled ? 'guest' : 'madfam',
  tierConfig: null,
  limits: null,
  allTiers: null,
  loading: true,
  canAccess: () => !isAuthEnabled,
}

export function TierProvider({ children }) {
  const { isAuthenticated } = useAuth()
  const [allTiers, setAllTiers] = useState(null)
  const [userInfo, setUserInfo] = useState(null)
  const [loading, setLoading] = useState(true)

  // Fetch tier definitions once
  useEffect(() => {
    fetch(`${getApiBase()}/api/tiers`)
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
  const limits = userInfo?.limits || (allTiers ? allTiers[tier] : null)

  const canAccess = useCallback((requiredTier) => {
    if (!isAuthEnabled) return true
    return (TIER_HIERARCHY[tier] ?? 0) >= (TIER_HIERARCHY[requiredTier] ?? 0)
  }, [tier])

  const value = {
    tier,
    tierConfig: allTiers?.[tier] || null,
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

// eslint-disable-next-line react-refresh/only-export-components
export function useTier() {
  return useContext(TierContext) || FALLBACK
}
