import { useState, useEffect, useCallback } from 'react'
import { Lightbulb } from 'lucide-react'
import { useLanguage } from '../../contexts/system/LanguageProvider'

const TIP_COUNT = 10
const TIP_DELAY_MS = 800
const TIP_INTERVAL_MS = 4000

export default function SplashScreen({ exiting = false }) {
  const { t } = useLanguage()
  const [tipIndex, setTipIndex] = useState(() => Math.floor(Math.random() * TIP_COUNT))
  const [showTips, setShowTips] = useState(false)
  const [tipVisible, setTipVisible] = useState(true)

  const prefersReducedMotion = typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    const delay = setTimeout(() => setShowTips(true), TIP_DELAY_MS)
    return () => clearTimeout(delay)
  }, [])

  const rotateTip = useCallback(() => {
    setTipVisible(false)
    setTimeout(() => {
      setTipIndex(i => (i + 1) % TIP_COUNT)
      setTipVisible(true)
    }, 200)
  }, [])

  useEffect(() => {
    if (!showTips || prefersReducedMotion) return
    const interval = setInterval(rotateTip, TIP_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [showTips, prefersReducedMotion, rotateTip])

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-background text-foreground transition-opacity duration-300 ${exiting ? 'opacity-0' : 'opacity-100'}`}
      role="status"
      aria-label={t('splash.loading')}
    >
      <svg width="48" height="48" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className="motion-safe:animate-pulse">
        <rect width="32" height="32" rx="6" fill="#3B82F6"/>
        <text x="16" y="22" textAnchor="middle" fontFamily="system-ui,sans-serif" fontWeight="800" fontSize="14" fill="white">4D</text>
      </svg>
      <span className="text-xl font-bold">Yantra4D</span>
      <div className="w-40 h-[3px] rounded-sm bg-muted-foreground/20 overflow-hidden">
        <div className="h-full w-2/5 rounded-sm bg-primary animate-indeterminate motion-reduce:animate-none motion-reduce:w-3/5" />
      </div>
      <span className="text-sm text-muted-foreground">{t('splash.loading')}</span>

      {showTips && (
        <div
          className="mt-4 flex items-center gap-2 text-sm text-muted-foreground max-w-xs text-center"
          aria-live="polite"
        >
          <Lightbulb className="h-4 w-4 shrink-0" />
          <span
            className={`transition-opacity duration-200 ${tipVisible ? 'opacity-100' : 'opacity-0'}`}
          >
            {t(`splash.tip_${tipIndex + 1}`)}
          </span>
        </div>
      )}
    </div>
  )
}
