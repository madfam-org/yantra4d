import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageProvider'
import { useManifest } from '../contexts/ManifestProvider'

export default function AssemblyView({ onStepChange }) {
  const { language, t } = useLanguage()
  const { manifest, getLabel } = useManifest()
  const steps = manifest?.assembly_steps
  const [currentStep, setCurrentStep] = useState(0)

  const step = steps?.[currentStep]

  const goTo = useCallback((idx) => {
    if (!steps) return
    const clamped = Math.max(0, Math.min(steps.length - 1, idx))
    setCurrentStep(clamped)
    const s = steps[clamped]
    onStepChange?.(s)
  }, [steps, onStepChange])

  // Notify parent of initial step when assembly steps first appear
  useEffect(() => {
    if (steps?.length > 0) {
      onStepChange?.(steps[0])
    }
    return () => {
      // Clear assembly state when component unmounts or steps disappear
      onStepChange?.(null)
    }
  }, [steps]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'ArrowRight') goTo(currentStep + 1)
      else if (e.key === 'ArrowLeft') goTo(currentStep - 1)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [currentStep, goTo])

  if (!steps || steps.length === 0) return null

  return (
    <div className="flex flex-col gap-3 border-t border-border pt-4">
      <h3 className="text-sm font-semibold">{t('assembly.title')}</h3>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="icon"
          className="min-h-[44px] min-w-[44px]"
          onClick={() => goTo(currentStep - 1)}
          disabled={currentStep === 0}
          aria-label={t('assembly.prev')}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 text-center">
          <span className="text-xs text-muted-foreground">
            {t('assembly.step')} {currentStep + 1} / {steps.length}
          </span>
        </div>
        <Button
          variant="outline"
          size="icon"
          className="min-h-[44px] min-w-[44px]"
          onClick={() => goTo(currentStep + 1)}
          disabled={currentStep === steps.length - 1}
          aria-label={t('assembly.next')}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
      {step && (
        <div className="bg-muted rounded-lg p-3 space-y-1">
          <p className="text-sm font-medium">{getLabel(step, 'label', language)}</p>
          {step.notes && (
            <p className="text-xs text-muted-foreground">{getLabel(step, 'notes', language)}</p>
          )}
        </div>
      )}
    </div>
  )
}
