import { useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { getApiBase } from "../services/backendDetection"
import { useLanguage } from "../contexts/LanguageProvider"
import { Upload, ChevronRight, ChevronLeft, Check, AlertTriangle } from "lucide-react"

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

  const updateManifestField = (path, value) => {
    setManifest((prev) => {
      const copy = JSON.parse(JSON.stringify(prev))
      const keys = path.split(".")
      let obj = copy
      for (let i = 0; i < keys.length - 1; i++) obj = obj[keys[i]]
      obj[keys[keys.length - 1]] = value
      return copy
    })
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

      {/* Step 0: Upload */}
      {step === 0 && (
        <div className="flex flex-col gap-4">
          <div className="text-lg font-semibold">{t("onboard.upload_title")}</div>

          <div>
            <label className="text-sm font-medium">{t("onboard.slug_label")}</label>
            <input
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value.replace(/[^a-z0-9-_]/gi, ""))}
              className="w-full mt-1 px-3 py-2 rounded-md border border-border bg-background text-sm"
              placeholder={t("onboard.slug_placeholder")}
            />
          </div>

          <div
            onDrop={handleFileDrop}
            onDragOver={(e) => e.preventDefault()}
            className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
          >
            <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              {t("onboard.drop_text")}
            </p>
            <input
              type="file"
              multiple
              accept=".scad"
              onChange={handleFileDrop}
              className="hidden"
              id="scad-upload"
            />
            <label htmlFor="scad-upload" className="text-primary text-sm underline cursor-pointer">
              {t("onboard.browse")}
            </label>
          </div>

          {files.length > 0 && (
            <div className="text-sm">
              <div className="font-medium mb-1">{files.length} {t("onboard.files_selected")}</div>
              <ul className="list-disc list-inside text-muted-foreground">
                {files.map((f) => (
                  <li key={f.name}>{f.name}</li>
                ))}
              </ul>
            </div>
          )}

          <Button onClick={handleAnalyze} disabled={files.length === 0 || loading}>
            {loading ? t("onboard.analyzing") : t("onboard.analyze_btn")}
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      )}

      {/* Step 1: Review Analysis */}
      {step === 1 && analysis && (
        <div className="flex flex-col gap-4">
          <div className="text-lg font-semibold">{t("onboard.review_title")}</div>

          {warnings.length > 0 && (
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-md p-3">
              <div className="flex items-center gap-1 text-sm font-medium text-yellow-700 dark:text-yellow-400 mb-1">
                <AlertTriangle className="h-4 w-4" /> {t("onboard.warnings")}
              </div>
              <ul className="list-disc list-inside text-sm text-muted-foreground">
                {warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {Object.entries(analysis.files).map(([fname, data]) => (
            <div key={fname} className="border border-border rounded-md p-3">
              <div className="font-mono text-sm font-semibold mb-2">{fname}</div>
              <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                <div>{t("onboard.variables")}: {data.variables.length}</div>
                <div>{t("onboard.modules")}: {data.modules.length}</div>
                <div>{t("onboard.includes")}: {data.includes.length}</div>
                <div>{t("onboard.render_modes")}: {data.render_modes.length > 0 ? data.render_modes.join(", ") : t("onboard.none")}</div>
              </div>
            </div>
          ))}

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setStep(0)}>
              <ChevronLeft className="h-4 w-4 mr-1" /> {t("onboard.back")}
            </Button>
            <Button onClick={() => setStep(2)}>
              {t("onboard.edit_manifest")} <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Edit Manifest */}
      {step === 2 && manifest && (
        <div className="flex flex-col gap-4">
          <div className="text-lg font-semibold">{t("onboard.edit_title")}</div>

          <div>
            <label className="text-sm font-medium">{t("onboard.project_name")}</label>
            <input
              type="text"
              value={manifest.project.name}
              onChange={(e) => updateManifestField("project.name", e.target.value)}
              className="w-full mt-1 px-3 py-2 rounded-md border border-border bg-background text-sm"
            />
          </div>

          <div>
            <label className="text-sm font-medium">{t("onboard.manifest_json")}</label>
            <textarea
              value={JSON.stringify(manifest, null, 2)}
              onChange={(e) => {
                try {
                  setManifest(JSON.parse(e.target.value))
                  setError(null)
                } catch {
                  setError(t("onboard.invalid_json"))
                }
              }}
              rows={20}
              className="w-full mt-1 px-3 py-2 rounded-md border border-border bg-background font-mono text-xs"
            />
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setStep(1)}>
              <ChevronLeft className="h-4 w-4 mr-1" /> {t("onboard.back")}
            </Button>
            <Button onClick={() => setStep(3)}>
              {t("onboard.review_save")} <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Save */}
      {step === 3 && (
        <div className="flex flex-col gap-4">
          <div className="text-lg font-semibold">{t("onboard.save_title")}</div>
          <div className="text-sm text-muted-foreground">
            {saveSummary}
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setStep(2)}>
              <ChevronLeft className="h-4 w-4 mr-1" /> {t("onboard.back")}
            </Button>
            <Button onClick={handleSave} disabled={loading}>
              {loading ? t("onboard.saving") : t("onboard.create_btn")}
              <Check className="h-4 w-4 ml-1" />
            </Button>
            {onCancel && (
              <Button variant="ghost" onClick={onCancel}>
                {t("onboard.cancel")}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
