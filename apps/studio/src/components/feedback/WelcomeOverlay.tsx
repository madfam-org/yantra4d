import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { Button } from '@/components/ui/button'

interface WelcomeFeature {
  icon: string
  text: Record<string, string> | string
}

interface WelcomeConfig {
  heading?: Record<string, string> | string
  body?: Record<string, string> | string
  features?: WelcomeFeature[]
  cta_label?: Record<string, string> | string
}

interface WelcomeOverlayProps {
  slug: string
  welcome: WelcomeConfig
}

function getLocalizedText(value: Record<string, string> | string | undefined, lang: string): string {
  if (!value) return ''
  if (typeof value === 'string') return value
  return value[lang] || value.en || value.es || ''
}

function getStorageKey(slug: string): string {
  return `yantra4d-welcome-${slug}`
}

export default function WelcomeOverlay({ slug, welcome }: WelcomeOverlayProps) {
  const { language } = useLanguage()
  const dialogRef = useRef<HTMLDivElement>(null)

  const [visible, setVisible] = useState(() => {
    try {
      return !localStorage.getItem(getStorageKey(slug))
    } catch {
      return true
    }
  })

  const dismiss = useCallback(() => {
    try {
      localStorage.setItem(getStorageKey(slug), 'true')
    } catch { /* quota exceeded or private browsing */ }
    setVisible(false)
  }, [slug])

  useEffect(() => {
    if (!visible) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        dismiss()
      }
    }
    window.addEventListener('keydown', handler, { capture: true })
    return () => window.removeEventListener('keydown', handler, { capture: true })
  }, [visible, dismiss])

  useEffect(() => {
    if (visible && dialogRef.current) {
      dialogRef.current.focus()
    }
  }, [visible])

  if (!visible) return null

  const heading = getLocalizedText(welcome.heading, language)
  const body = getLocalizedText(welcome.body, language)
  const features = welcome.features || []
  const ctaLabel = getLocalizedText(welcome.cta_label, language) || 'Get Started'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300"
      role="presentation"
      onMouseDown={dismiss}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="welcome-heading"
        tabIndex={-1}
        className="relative w-full max-w-md mx-4 max-h-[90dvh] overflow-y-auto rounded-2xl border border-border bg-card shadow-xl p-6 sm:p-8 motion-safe:animate-in motion-safe:zoom-in-95 motion-safe:duration-300 outline-none"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {heading && (
          <h2 id="welcome-heading" className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground mb-3">
            {heading}
          </h2>
        )}

        {body && (
          <p className="text-muted-foreground text-sm sm:text-base leading-relaxed mb-6">
            {body}
          </p>
        )}

        {features.length > 0 && (
          <ul className="space-y-3 mb-6">
            {features.map((feature, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="text-xl shrink-0 mt-0.5" aria-hidden="true">{feature.icon}</span>
                <span className="text-sm text-foreground leading-relaxed">
                  {getLocalizedText(feature.text, language)}
                </span>
              </li>
            ))}
          </ul>
        )}

        <Button
          onClick={dismiss}
          className="w-full min-h-[44px] text-base font-semibold"
          data-testid="welcome-cta"
        >
          {ctaLabel}
        </Button>
      </div>
    </div>
  )
}
