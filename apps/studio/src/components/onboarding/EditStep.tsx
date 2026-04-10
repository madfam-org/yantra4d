import React, { useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"

interface EditStepProps {
  manifest: Record<string, unknown>
  setManifest: React.Dispatch<React.SetStateAction<Record<string, unknown> | null>>
  onBack: () => void
  onNext: () => void
  t: (key: string) => string
}

export default function EditStep({ manifest, setManifest, onBack, onNext, t }: EditStepProps) {
  const [showRawJson, setShowRawJson] = useState(false)
  const [jsonError, setJsonError] = useState<string | null>(null)

  const updateManifestField = (path: string, value: unknown) => {
    setManifest((prev) => {
      if (!prev) return prev
      const copy = JSON.parse(JSON.stringify(prev))
      const keys = path.split(".")
      let obj = copy
      for (let i = 0; i < keys.length - 1; i++) obj = obj[keys[i]]
      obj[keys[keys.length - 1]] = value
      return copy
    })
  }

  const project = manifest.project as Record<string, unknown>
  const modes = manifest.modes as Array<Record<string, unknown>> || []
  const parameters = manifest.parameters as Array<Record<string, unknown>> || []
  const parts = manifest.parts as Array<Record<string, unknown>> || []

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="text-lg font-semibold">{t("onboard.edit_title")}</div>
        <button
          type="button"
          className="text-xs text-muted-foreground hover:text-foreground underline min-h-[44px]"
          onClick={() => setShowRawJson(prev => !prev)}
        >
          {showRawJson ? t("onboard.structured_view") : t("onboard.raw_json")}
        </button>
      </div>

      {showRawJson ? (
        <div>
          <label className="text-sm font-medium">{t("onboard.manifest_json")}</label>
          <textarea
            value={JSON.stringify(manifest, null, 2)}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => {
              try {
                const parsed = JSON.parse(e.target.value)
                setManifest(parsed)
                setJsonError(null)
              } catch (err: unknown) {
                setJsonError(`Invalid JSON: ${err instanceof Error ? err.message : String(err)}`)
              }
            }}
            rows={12}
            className={`w-full mt-1 px-3 py-2 rounded-md border bg-background font-mono text-base sm:text-xs ${jsonError ? 'border-destructive' : 'border-border'}`}
            aria-invalid={!!jsonError}
          />
          {jsonError && (
            <p className="text-xs text-destructive mt-1">{jsonError}</p>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {/* Project name */}
          <div>
            <label className="text-sm font-medium">{t("onboard.project_name")}</label>
            <input
              type="text"
              value={project.name as string}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateManifestField("project.name", e.target.value)}
              className="w-full mt-1 px-3 py-2 rounded-md border border-border bg-background text-base sm:text-sm"
            />
          </div>

          {/* Modes as cards */}
          <div>
            <label className="text-sm font-medium">{t("onboard.modes_label")}</label>
            <div className="grid gap-2 mt-1">
              {modes.map((mode, idx) => (
                <div key={idx} className="border border-border rounded-md p-3 space-y-2">
                  <div className="flex flex-col sm:flex-row gap-2">
                    <input
                      type="text"
                      value={mode.id as string}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                        const newModes = [...modes]
                        newModes[idx] = { ...newModes[idx], id: e.target.value }
                        setManifest(prev => prev ? { ...prev, modes: newModes } : prev)
                      }}
                      className="flex-1 px-2 py-1 text-base sm:text-sm rounded border border-border bg-background min-h-[44px]"
                      placeholder="Mode ID"
                    />
                    <input
                      type="text"
                      value={typeof mode.label === 'string' ? mode.label : (mode.label as Record<string, string>)?.en || ''}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                        const newModes = [...modes]
                        newModes[idx] = { ...newModes[idx], label: e.target.value }
                        setManifest(prev => prev ? { ...prev, modes: newModes } : prev)
                      }}
                      className="flex-1 px-2 py-1 text-base sm:text-sm rounded border border-border bg-background min-h-[44px]"
                      placeholder="Label"
                    />
                  </div>
                  <div className="text-xs text-muted-foreground">{mode.scad_file as string}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Parameters table */}
          <div>
            <label className="text-sm font-medium">{t("onboard.params_label")}</label>
            <div className="overflow-x-auto mt-1">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="py-1 pr-2">ID</th>
                    <th className="py-1 pr-2">Type</th>
                    <th className="py-1 pr-2">Default</th>
                    <th className="py-1 pr-2">Min</th>
                    <th className="py-1">Max</th>
                  </tr>
                </thead>
                <tbody>
                  {parameters.map((param, idx) => (
                    <tr key={idx} className="border-b border-border/50">
                      <td className="py-1 pr-2 font-mono">{param.id as string}</td>
                      <td className="py-1 pr-2">{param.type as string}</td>
                      <td className="py-1 pr-2">
                        <input
                          type={param.type === 'slider' ? 'number' : 'text'}
                          value={param.default != null ? String(param.default) : ''}
                          onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                            const newParameters = [...parameters]
                            const val = param.type === 'slider' ? parseFloat(e.target.value) || 0 : e.target.value
                            newParameters[idx] = { ...newParameters[idx], default: val }
                            setManifest(prev => prev ? { ...prev, parameters: newParameters } : prev)
                          }}
                          className="w-20 md:w-16 px-2 md:px-1 py-2 sm:py-0.5 min-h-[44px] md:min-h-0 rounded border border-border bg-background text-base sm:text-xs"
                        />
                      </td>
                      <td className="py-1 pr-2">
                        {param.type === 'slider' && (
                          <input
                            type="number"
                            value={param.min != null ? String(param.min) : ''}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                              const newParameters = [...parameters]
                              newParameters[idx] = { ...newParameters[idx], min: parseFloat(e.target.value) || 0 }
                              setManifest(prev => prev ? { ...prev, parameters: newParameters } : prev)
                            }}
                            className="w-18 md:w-14 px-2 md:px-1 py-2 sm:py-0.5 min-h-[44px] md:min-h-0 rounded border border-border bg-background text-base sm:text-xs"
                          />
                        )}
                      </td>
                      <td className="py-1">
                        {param.type === 'slider' && (
                          <input
                            type="number"
                            value={param.max != null ? String(param.max) : ''}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                              const newParameters = [...parameters]
                              newParameters[idx] = { ...newParameters[idx], max: parseFloat(e.target.value) || 0 }
                              setManifest(prev => prev ? { ...prev, parameters: newParameters } : prev)
                            }}
                            className="w-18 md:w-14 px-2 md:px-1 py-2 sm:py-0.5 min-h-[44px] md:min-h-0 rounded border border-border bg-background text-base sm:text-xs"
                          />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Part colors */}
          {parts.length > 0 && (
            <div>
              <label className="text-sm font-medium">{t("onboard.parts_label")}</label>
              <div className="grid grid-cols-2 gap-2 mt-1">
                {parts.map((part, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="text-xs">{part.id as string}</span>
                    <input
                      type="color"
                      value={(part.default_color as string) || '#888888'}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                        const newParts = [...parts]
                        newParts[idx] = { ...newParts[idx], default_color: e.target.value }
                        setManifest(prev => prev ? { ...prev, parts: newParts } : prev)
                      }}
                      className="w-10 h-10 min-h-[44px] min-w-[44px] cursor-pointer"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <Button variant="outline" onClick={onBack}>
          <ChevronLeft className="h-4 w-4 mr-1" /> {t("onboard.back")}
        </Button>
        <Button onClick={onNext}>
          {t("onboard.review_save")} <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  )
}
