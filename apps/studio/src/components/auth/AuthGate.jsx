import { useAuth, isAuthEnabled } from "../../contexts/AuthProvider"
import { useManifest } from "../../contexts/ManifestProvider"
import { useTier } from "../../hooks/useTier"

/**
 * Conditionally renders children based on manifest access_control, auth state, and tier.
 *
 * @param {string} action - Key in manifest.access_control (e.g., "download_stl")
 * @param {string} tier - Minimum tier required (e.g., "pro", "madfam")
 * @param {React.ReactNode} children - Content to show when access is granted
 * @param {React.ReactNode} fallback - Content to show when access is denied (optional)
 */
export default function AuthGate({ action, tier: requiredTier, children, fallback = null }) {
  const { isAuthenticated } = useAuth()
  const { manifest } = useManifest()
  const { canAccess } = useTier()

  // If auth is not configured, always show children
  if (!isAuthEnabled) return children

  // Tier-based gating
  if (requiredTier && !canAccess(requiredTier)) return fallback

  // Manifest access_control gating
  if (action) {
    const accessControl = manifest?.access_control || {}
    const level = accessControl[action] || "public"

    if (level === "public") return children
    if (level === "authenticated" && isAuthenticated) return children

    // If we have an action check and it failed, show fallback
    if (level !== "public") return fallback
  }

  return children
}
