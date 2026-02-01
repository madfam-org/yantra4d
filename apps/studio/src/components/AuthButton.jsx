import { Button } from "@/components/ui/button"
import { LogIn, LogOut } from 'lucide-react'
import { useAuth, isAuthEnabled } from "../contexts/AuthProvider"
import { useLanguage } from "../contexts/LanguageProvider"

export default function AuthButton() {
  const { t } = useLanguage()
  const { user, isAuthenticated, isLoading, signOut, signInWithOAuth } = useAuth()

  if (!isAuthEnabled) return null

  if (isLoading) {
    return (
      <Button variant="ghost" size="sm" disabled className="gap-2 text-xs">
        ...
      </Button>
    )
  }

  if (isAuthenticated && user) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground hidden sm:inline">
          {user.display_name || user.email}
        </span>
        <Button variant="ghost" size="sm" onClick={() => signOut()} className="gap-1" title={t('auth.sign_out')}>
          <LogOut className="h-4 w-4" />
          <span className="sr-only">{t('auth.sign_out')}</span>
        </Button>
      </div>
    )
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => signInWithOAuth('github')}
      className="gap-1"
      title={t('auth.sign_in')}
    >
      <LogIn className="h-4 w-4" />
      <span className="text-xs">{t('auth.sign_in')}</span>
    </Button>
  )
}
