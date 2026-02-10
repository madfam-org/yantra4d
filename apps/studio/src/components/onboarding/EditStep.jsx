import { useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function EditStep({ manifest, setManifest, onBack, onNext, t }) {
  const [showRawJson, setShowRawJson] = useState(false)
  const [jsonError, setJsonError] = useState(null)

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

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="text-lg font-semibold">{t("onboard.edit_title")}</div>
        <button
          type="button"
          className="text-xs text-muted-foreground hover:text-foreground underline"
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
            onChange={(e) => {
              try {
                const parsed = JSON.parse(e.target.value)
                setManifest(parsed)
                setJsonError(null)
              } catch (err) {
                setJsonError(`Invalid JSON: ${err.message}`)
              }
            }}
            rows={20}
            className={`w-full mt-1 px-3 py-2 rounded-md border bg-background font-mono text-xs ${jsonError ? 'border-destructive' : 'border-border'}`}
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
              value={manifest.project.name}
              onChange={(e) => updateManifestField("project.name", e.target.value)}
              className="w-full mt-1 px-3 py-2 rounded-md border border-border bg-background text-sm"
            />
          </div>

          {/* Modes as cards */}
          <div>
            <label className="text-sm font-medium">{t("onboard.modes_label")}</label>
            <div className="grid gap-2 mt-1">
              {(manifest.modes || []).map((mode, idx) => (
                <div key={idx} className="border border-border rounded-md p-3 space-y-2">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={mode.id}
                      onChange={(e) => {
                        const modes = [...manifest.modes]
                        modes[idx] = { ...modes[idx], id: e.target.value }
                        setManifest(prev => ({ ...prev, modes }))
                      }}
                      className="flex-1 px-2 py-1 text-sm rounded border border-border bg-background"
                      placeholder="Mode ID"
                    />
                    <input
                      type="text"
                      value={typeof mode.label === 'string' ? mode.label : mode.label?.en || ''}
                      onChange={(e) => {
                        const modes = [...manifest.modes]
                        modes[idx] = { ...modes[idx], label: e.target.value }
                        setManifest(prev => ({ ...prev, modes }))
                      }}
                      className="flex-1 px-2 py-1 text-sm rounded border border-border bg-background"
                      placeholder="Label"
                    />
                  </div>
                  <div className="text-xs text-muted-foreground">{mode.scad_file}</div>
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
                  {(manifest.parameters || []).map((param, idx) => (
                    <tr key={idx} className="border-b border-border/50">
                      <td className="py-1 pr-2 font-mono">{param.id}</td>
                      <td className="py-1 pr-2">{param.type}</td>
                      <td className="py-1 pr-2">
                        <input
                          type={param.type === 'slider' ? 'number' : 'text'}
                          value={param.default ?? ''}
                          onChange={(e) => {
                            const parameters = [...manifest.parameters]
                            const val = param.type === 'slider' ? parseFloat(e.target.value) || 0 : e.target.value
                            parameters[idx] = { ...parameters[idx], default: val }
                            setManifest(prev => ({ ...prev, parameters }))
                          }}
                          className="w-16 px-1 py-0.5 rounded border border-border bg-background text-xs"
                        />
                      </td>
                      <td className="py-1 pr-2">
                        {param.type === 'slider' && (
                          <input
                            type="number"
                            value={param.min ?? ''}
                            onChange={(e) => {
                              const parameters = [...manifest.parameters]
                              parameters[idx] = { ...parameters[idx], min: parseFloat(e.target.value) || 0 }
                              setManifest(prev => ({ ...prev, parameters }))
                            }}
                            className="w-14 px-1 py-0.5 rounded border border-border bg-background text-xs"
                          />
                        )}
                      </td>
                      <td className="py-1">
                        {param.type === 'slider' && (
                          <input
                            type="number"
                            value={param.max ?? ''}
                            onChange={(e) => {
                              const parameters = [...manifest.parameters]
                              parameters[idx] = { ...parameters[idx], max: parseFloat(e.target.value) || 0 }
                              setManifest(prev => ({ ...prev, parameters }))
                            }}
                            className="w-14 px-1 py-0.5 rounded border border-border bg-background text-xs"
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
          {(manifest.parts || []).length > 0 && (
            <div>
              <label className="text-sm font-medium">{t("onboard.parts_label")}</label>
              <div className="grid grid-cols-2 gap-2 mt-1">
                {manifest.parts.map((part, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="text-xs">{part.id}</span>
                    <input
                      type="color"
                      value={part.default_color || '#888888'}
                      onChange={(e) => {
                        const parts = [...manifest.parts]
                        parts[idx] = { ...parts[idx], default_color: e.target.value }
                        setManifest(prev => ({ ...prev, parts }))
                      }}
                      className="w-8 h-6 cursor-pointer"
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
