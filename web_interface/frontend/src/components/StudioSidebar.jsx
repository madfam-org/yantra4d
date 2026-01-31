import Controls from './Controls'
import ExportPanel from './ExportPanel'
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Square, RotateCcw } from 'lucide-react'

export default function StudioSidebar({
  manifest, mode, setMode, getLabel, language, t,
  params, setParams, colors, setColors, wireframe, setWireframe,
  presets, handleApplyPreset, handleGridPresetToggle,
  loading, parts,
  handleGenerate, handleCancelGenerate, handleVerify, handleReset,
  handleDownloadStl, handleExportImage, handleExportAllViews,
  exportFormat, setExportFormat,
}) {
  return (
    <div className="w-full lg:w-80 lg:min-w-[20rem] border-b lg:border-b-0 lg:border-r border-border bg-card p-4 flex flex-col gap-4 overflow-y-auto shrink-0 max-h-[50vh] lg:max-h-none">
      <Tabs value={mode} onValueChange={setMode} className="w-full relative z-10">
        <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${manifest.modes.length}, minmax(0, 1fr))` }}>
          {manifest.modes.map(m => (
            <TabsTrigger key={m.id} value={m.id} className="min-h-[44px]">
              {getLabel(m, 'label', language)}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <Controls
        params={params}
        setParams={setParams}
        mode={mode}
        colors={colors}
        setColors={setColors}
        wireframe={wireframe}
        setWireframe={setWireframe}
        presets={presets}
        onApplyPreset={handleApplyPreset}
        onToggleGridPreset={handleGridPresetToggle}
      />

      <div className="flex-1"></div>

      <div className="flex flex-col gap-2 border-t border-border pt-4">
        <Button
          type="button"
          onClick={() => handleGenerate()}
          disabled={loading}
          className="w-full"
          title={t("tooltip.gen")}
        >
          {loading ? t("btn.proc") : t("btn.gen")}
        </Button>

        {loading && (
          <Button variant="destructive" onClick={handleCancelGenerate} className="w-full gap-2">
            <Square className="h-4 w-4" />
            {t("btn.cancel")}
          </Button>
        )}

        <Button
          variant="secondary"
          onClick={handleVerify}
          disabled={loading || parts.length === 0}
          className="w-full"
          title={t("tooltip.verify")}
        >
          {t("btn.verify")}
        </Button>

        <Button variant="outline" onClick={handleReset} className="w-full gap-2">
          <RotateCcw className="h-4 w-4" />
          {t("btn.reset")}
        </Button>
      </div>

      <ExportPanel
        parts={parts}
        mode={mode}
        onDownloadStl={handleDownloadStl}
        onExportImage={handleExportImage}
        onExportAllViews={handleExportAllViews}
        exportFormat={exportFormat}
        onExportFormatChange={setExportFormat}
      />
    </div>
  )
}
