import { useAuth, isAuthEnabled } from "../contexts/AuthProvider"
import { useManifest } from "../contexts/ManifestProvider"

/**
 * Conditionally renders children based on manifest access_control and auth state.
 *
 * @param {string} action - Key in manifest.access_control (e.g., "download_stl")
 * @param {React.ReactNode} children - Content to show when access is granted
 * @param {React.ReactNode} fallback - Content to show when access is denied (optional)
 */
export default function AuthGate({ action, children, fallback = null }) {
  const { isAuthenticated } = useAuth()
  const { manifest } = useManifest()

  // If auth is not configured, always show children
  if (!isAuthEnabled) return children

  const accessControl = manifest?.access_control || {}
  const level = accessControl[action] || "public"

  if (level === "public") return children
  if (level === "authenticated" && isAuthenticated) return children

  return fallback
}
