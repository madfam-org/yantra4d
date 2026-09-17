import { useSession, UserProfile } from "@janua/react-sdk"
import { Button } from "@/components/ui/button"
import { LogIn, LogOut } from 'lucide-react'
import { useAuth, isAuthEnabled } from "../../contexts/auth/AuthProvider"
import { useLanguage } from "../../contexts/system/LanguageProvider"
import { getStoredIdentityEmail } from "../../lib/januaSso"

function AuthButtonInner() {
  const { t } = useLanguage()
  const { signInWithJanua, signOut, isAuthenticated } = useAuth()
  const { session } = useSession()

  // Products whose users sign in through the SDK's own flow keep its profile widget.
  if (session) {
    return <UserProfile />
  }

  // The Studio's OIDC/PKCE flow (lib/januaSso.ts) stores tokens but never
  // populates the SDK's `session`/`user`: the SDK loads `user` from Janua's
  // GET /api/v1/auth/me, which rejects a yantra4d-api-audience token with 401.
  // So `session` stays null even when signed in. Drive the account control off
  // the real (stored-token) session instead — otherwise a signed-in user sees a
  // "sign in" button that only bounces them through their existing Janua session.
  if (isAuthenticated) {
    const email = getStoredIdentityEmail()
    return (
      <div className="flex items-center gap-1">
        {email && (
          <span
            className="text-xs text-muted-foreground max-w-[12rem] truncate hidden sm:inline"
            title={email}
          >
            {email}
          </span>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            // The SDK's signOut clears the stored tokens AND drops the Janua
            // session cookie (client.signOut()), so the next sign-in shows the
            // login form instead of silently resuming the session. Reload to a
            // clean signed-out state regardless of the server call's outcome.
            void signOut().finally(() => { window.location.href = '/' })
          }}
          className="gap-1"
          title={t('auth.sign_out')}
        >
          <LogOut className="h-4 w-4" />
          <span className="text-xs">{t('auth.sign_out')}</span>
        </Button>
      </div>
    )
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => {
        signInWithJanua().catch((err: unknown) => console.error('Sign-in could not start:', err))
      }}
      className="gap-1"
      title={t('auth.sign_in')}
    >
      <LogIn className="h-4 w-4" />
      <span className="text-xs">{t('auth.sign_in')}</span>
    </Button>
  )
}

export default function AuthButton() {
  if (!isAuthEnabled) return null
  return <AuthButtonInner />
}
