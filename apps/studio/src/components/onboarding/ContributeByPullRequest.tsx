/**
 * What /onboard shows to everyone who is not a platform administrator.
 *
 * Uploading `.scad` files (`POST /api/projects/analyze` and `/create`) is
 * platform-admin only (`@require_platform_admin`, apps/api/routes/users/
 * onboard.py), so the wizard could only ever fail for anyone else, at the API,
 * after they had picked their files. New designs reach the Hyperobjects
 * Commons by pull request to its repository (PRODUCT.md, "Contributions"):
 * this page says so and links to that repository's contribution guide.
 *
 * Laid out like the Studio's other standalone pages (the manifest error page
 * in App.tsx): centred, one heading, one paragraph, the way forward as buttons.
 */
import { ExternalLink, GitPullRequest } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useAuth, isAuthEnabled } from '../../contexts/auth/AuthProvider'
import AuthButton from '../auth/AuthButton'

/** The Commons repository's own guide (madfam-org/solid-hyperobjects, CONTRIBUTING.md). */
export const COMMONS_CONTRIBUTING_URL = 'https://github.com/madfam-org/solid-hyperobjects/blob/main/CONTRIBUTING.md'

interface ContributeByPullRequestProps {
  /** Go to the catalog. */
  onBrowse: () => void
}

export default function ContributeByPullRequest({ onBrowse }: ContributeByPullRequestProps) {
  const { t } = useLanguage()
  const { isAuthenticated } = useAuth()

  return (
    <main
      data-testid="onboard-contribute"
      className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-background px-4 py-10 text-center text-foreground"
    >
      <GitPullRequest className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
      <h1 className="max-w-lg text-2xl font-bold [text-wrap:balance]">{t('onboard.closed_title')}</h1>
      <p className="max-w-md text-muted-foreground">{t('onboard.closed_body')}</p>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button asChild className="min-h-[44px]">
          <a href={COMMONS_CONTRIBUTING_URL} target="_blank" rel="noopener noreferrer">
            {t('onboard.closed_guide')}
            <ExternalLink aria-hidden="true" />
            <span className="sr-only">{t('a11y.opens_new_tab')}</span>
          </a>
        </Button>
        <Button variant="outline" className="min-h-[44px]" onClick={onBrowse}>
          {t('error.browse_projects')}
        </Button>
      </div>
      {isAuthEnabled && !isAuthenticated && (
        <div className="mt-2 flex flex-col items-center gap-2 text-sm text-muted-foreground">
          <p>{t('onboard.closed_admin_sign_in')}</p>
          <AuthButton />
        </div>
      )}
    </main>
  )
}
