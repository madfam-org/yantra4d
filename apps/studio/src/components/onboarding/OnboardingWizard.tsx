import React, { useState, useCallback } from "react"
import { apiFetch } from "../../services/core/apiClient"
import { getApiBase } from "../../services/core/backendDetection"
import { useLanguage } from "../../contexts/system/LanguageProvider"
import UploadStep from "./UploadStep"
import ReviewStep from "./ReviewStep"
import EditStep from "./EditStep"
import SaveStep from "./SaveStep"

const STEP_KEYS = ["onboard.step_upload", "onboard.step_review", "onboard.step_edit", "onboard.step_save"]

interface OnboardingWizardProps {
  onComplete?: () => void
  onCancel?: () => void
}

export default function OnboardingWizard({ onComplete, onCancel }: OnboardingWizardProps) {
  const { t } = useLanguage()
  const [step, setStep] = useState(0)
  const [files, setFiles] = useState<File[]>([])
  const [slug, setSlug] = useState("new-project")
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null)
  const [manifest, setManifest] = useState<Record<string, unknown> | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFileDrop = useCallback((e: React.DragEvent | React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    const dropped = Array.from(
      (e as React.DragEvent).dataTransfer?.files ||
      (e as React.ChangeEvent<HTMLInputElement>).target.files ||
      []
    )
    const scadFiles = dropped.filter((f) => f.name.endsWith(".scad"))
    setFiles((prev) => [...prev, ...scadFiles])
  }, [])

  const handleAnalyze = async () => {
    if (files.length === 0) return
    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append("slug", slug)
    files.forEach((f) => formData.append("files", f))

    try {
      const res = await apiFetch(`${getApiBase()}/api/projects/analyze`, {
        method: "POST",
        body: formData,
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || `HTTP ${res.status}`)
      }
      const data = await res.json()
      if (!data.manifest?.project || !data.manifest?.modes) {
        throw new Error('Server returned an incomplete manifest (missing project or modes)')
      }
      setAnalysis(data.analysis)
      setManifest(data.manifest)
      setWarnings(data.warnings || [])
      setStep(1)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append("manifest", JSON.stringify(manifest))
    files.forEach((f) => formData.append("files", f))

    try {
      const res = await apiFetch(`${getApiBase()}/api/projects/create`, {
        method: "POST",
        body: formData,
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || `HTTP ${res.status}`)
      }
      onComplete?.()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const saveSummary = t("onboard.save_summary")
    .replace("{name}", (manifest?.project as Record<string, unknown>)?.name as string || "")
    .replace("{slug}", (manifest?.project as Record<string, unknown>)?.slug as string || "")
    .replace("{files}", String(files.length))
    .replace("{modes}", String((manifest?.modes as unknown[])?.length || 0))
    .replace("{params}", String((manifest?.parameters as unknown[])?.length || 0))

  return (
    // The onboarding route renders standalone, without the app header, so E2E
    // specs need an anchor of their own to wait on.
    <div data-testid="onboarding-wizard" className="flex flex-col gap-4 p-4 sm:p-6 max-w-2xl mx-auto">
      {/* Step indicator */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
        {STEP_KEYS.map((key, i) => (
          <span key={key} className={`${i === step ? "text-foreground font-semibold" : ""}`}>
            {i > 0 && <span className="mx-1">›</span>}
            {t(key)}
          </span>
        ))}
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive px-4 py-2 rounded-md text-sm">
          {error}
        </div>
      )}

      {step === 0 && (
        <UploadStep
          slug={slug}
          setSlug={setSlug}
          files={files}
          handleFileDrop={handleFileDrop}
          handleAnalyze={handleAnalyze}
          loading={loading}
          t={t}
        />
      )}

      {step === 1 && analysis && (
        <ReviewStep
          analysis={analysis}
          warnings={warnings}
          onBack={() => setStep(0)}
          onNext={() => setStep(2)}
          t={t}
        />
      )}

      {step === 2 && manifest && (
        <EditStep
          manifest={manifest}
          setManifest={setManifest}
          onBack={() => setStep(1)}
          onNext={() => setStep(3)}
          t={t}
        />
      )}

      {step === 3 && (
        <SaveStep
          saveSummary={saveSummary}
          onBack={() => setStep(2)}
          onSave={handleSave}
          onCancel={onCancel}
          loading={loading}
          t={t}
        />
      )}
    </div>
  )
}
