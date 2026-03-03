import { UserButton, SignedIn, SignedOut } from "@janua/react-sdk"
import { Button } from "@/components/ui/button"
import { LogIn } from 'lucide-react'
import { useAuth, isAuthEnabled } from "../../contexts/auth/AuthProvider"
import { useLanguage } from "../../contexts/system/LanguageProvider"

export default function AuthButton() {
  const { t } = useLanguage()
  const { signInWithOAuth } = useAuth()

  if (!isAuthEnabled) return null

  return (
    <>
      <SignedIn>
        <UserButton showManageAccount={false} />
      </SignedIn>
      <SignedOut>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => signInWithOAuth('google')}
          className="gap-1"
          title={t('auth.sign_in')}
        >
          <LogIn className="h-4 w-4" />
          <span className="text-xs">{t('auth.sign_in')}</span>
        </Button>
      </SignedOut>
    </>
  )
}
