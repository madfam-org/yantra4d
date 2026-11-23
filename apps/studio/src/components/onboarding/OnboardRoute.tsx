/**
 * The /onboard route: the upload wizard for platform administrators, and for
 * everyone else the way new designs actually join the Commons.
 *
 * "Platform administrator" is the token's `is_admin` claim, the one the API's
 * `@require_platform_admin` checks on `/api/projects/analyze` and `/create`
 * (read from the stored session, lib/januaSso.ts). With auth off the API lets
 * every caller through that decorator, so the wizard is offered too: that is
 * local development and the e2e build.
 */
import { useNavigate } from 'react-router-dom'
import { isAuthEnabled, useAuth } from '../../contexts/auth/AuthProvider'
import { hasStoredPlatformAdminClaim } from '../../lib/januaSso'
import OnboardingWizard from './OnboardingWizard'
import ContributeByPullRequest from './ContributeByPullRequest'

/**
 * Whether this visitor may upload cartridges, as the API will decide it:
 * auth off, or a live session whose token carries the platform-admin claim.
 */
export function canUploadCartridges(isAuthenticated: boolean): boolean {
  return !isAuthEnabled || (isAuthenticated && hasStoredPlatformAdminClaim())
}

export default function OnboardRoute() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  if (canUploadCartridges(isAuthenticated)) return <OnboardingWizard />
  return <ContributeByPullRequest onBrowse={() => navigate('/projects')} />
}
