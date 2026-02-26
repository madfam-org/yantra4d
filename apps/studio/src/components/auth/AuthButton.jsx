import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { LogIn, LogOut } from 'lucide-react'
import { useAuth, isAuthEnabled } from "../../contexts/auth/AuthProvider"
import { useLanguage } from "../../contexts/system/LanguageProvider"

const OAUTH_PROVIDERS = [
  { id: 'google', label: 'Google' },
  { id: 'github', label: 'GitHub' },
  { id: 'microsoft', label: 'Microsoft' },
  { id: 'apple', label: 'Apple' },
]

export default function AuthButton() {
  const { t } = useLanguage()
  const { user, isAuthenticated, isLoading, signOut, signInWithOAuth } = useAuth()
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

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
    <div className="relative" ref={menuRef}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen((prev) => !prev)}
        className="gap-1"
        title={t('auth.sign_in')}
      >
        <LogIn className="h-4 w-4" />
        <span className="text-xs">{t('auth.sign_in')}</span>
      </Button>
      {open && (
        <div className="absolute right-0 top-full mt-1 z-50 min-w-[180px] rounded-md border bg-popover p-1 shadow-md">
          {OAUTH_PROVIDERS.map((provider) => (
            <button
              key={provider.id}
              className="w-full rounded-sm px-3 py-3 md:py-1.5 text-left text-base md:text-sm hover:bg-accent hover:text-accent-foreground min-h-[44px] md:min-h-0"
              onClick={() => {
                setOpen(false)
                signInWithOAuth(provider.id)
              }}
            >
              {t('auth.sign_in_with') || 'Sign in with'} {provider.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
