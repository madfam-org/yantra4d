import { useSession, UserProfile } from "@janua/react-sdk"
import { Button } from "@/components/ui/button"
import { LogIn } from 'lucide-react'
import { useAuth, isAuthEnabled } from "../../contexts/auth/AuthProvider"
import { useLanguage } from "../../contexts/system/LanguageProvider"

function AuthButtonInner() {
  const { t } = useLanguage()
  const { signInWithJanua } = useAuth()
  const { session } = useSession()

  if (session) {
    return <UserProfile />
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
