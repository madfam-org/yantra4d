import { useState, useCallback } from "react"
import { getApiBase } from "../../services/core/backendDetection"
import { useLanguage } from "../../contexts/system/LanguageProvider"
import UploadStep from "./UploadStep"
import ReviewStep from "./ReviewStep"
import EditStep from "./EditStep"
import SaveStep from "./SaveStep"

const STEP_KEYS = ["onboard.step_upload", "onboard.step_review", "onboard.step_edit", "onboard.step_save"]

export default function OnboardingWizard({ onComplete, onCancel }) {
  const { t } = useLanguage()
  const [step, setStep] = useState(0)
  const [files, setFiles] = useState([])
  const [slug, setSlug] = useState("new-project")
  const [analysis, setAnalysis] = useState(null)
  const [manifest, setManifest] = useState(null)
  const [warnings, setWarnings] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleFileDrop = useCallback((e) => {
    e.preventDefault()
    const dropped = Array.from(e.dataTransfer?.files || e.target.files || [])
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
      const res = await fetch(`${getApiBase()}/api/projects/analyze`, {
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
    } catch (e) {
      setError(e.message)
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
      const res = await fetch(`${getApiBase()}/api/projects/create`, {
        method: "POST",
        body: formData,
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || `HTTP ${res.status}`)
      }
      onComplete?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const saveSummary = t("onboard.save_summary")
    .replace("{name}", manifest?.project?.name || "")
    .replace("{slug}", manifest?.project?.slug || "")
    .replace("{files}", files.length)
    .replace("{modes}", manifest?.modes?.length || 0)
    .replace("{params}", manifest?.parameters?.length || 0)

  return (
    <div className="flex flex-col gap-4 p-6 max-w-2xl mx-auto">
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
