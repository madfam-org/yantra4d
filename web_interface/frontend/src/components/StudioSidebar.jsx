import { useState } from 'react'
import Controls from './Controls'
import ExportPanel from './ExportPanel'
import BomPanel from './BomPanel'
import AssemblyView from './AssemblyView'
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet"
import { Square, RotateCcw, Menu } from 'lucide-react'

function SidebarContent({
  manifest, mode, setMode, getLabel, language, t,
  params, setParams, colors, setColors, wireframe, setWireframe,
  presets, handleApplyPreset, handleGridPresetToggle,
  loading, parts,
  handleGenerate, handleCancelGenerate, handleVerify, handleReset,
  handleDownloadStl, handleExportImage, handleExportAllViews,
  exportFormat, setExportFormat,
  constraintsByParam, constraintErrors,
}) {
  return (
    <>
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
        constraintsByParam={constraintsByParam}
      />

      <div className="flex-1"></div>

      <div className="flex flex-col gap-2 border-t border-border pt-4">
        <Button
          type="button"
          onClick={() => handleGenerate()}
          disabled={loading || constraintErrors}
          className="w-full min-h-[44px]"
          title={t("tooltip.gen")}
        >
          {loading ? t("btn.proc") : t("btn.gen")}
        </Button>

        {loading && (
          <Button variant="destructive" onClick={handleCancelGenerate} className="w-full gap-2 min-h-[44px]">
            <Square className="h-4 w-4" />
            {t("btn.cancel")}
          </Button>
        )}

        <Button
          variant="secondary"
          onClick={handleVerify}
          disabled={loading || parts.length === 0}
          className="w-full min-h-[44px]"
          title={t("tooltip.verify")}
        >
          {t("btn.verify")}
        </Button>

        <Button variant="outline" onClick={handleReset} className="w-full gap-2 min-h-[44px]">
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

      <BomPanel params={params} />
      <AssemblyView />
    </>
  )
}

export default function StudioSidebar(props) {
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden lg:flex w-80 min-w-[20rem] border-r border-border bg-card p-4 flex-col gap-4 overflow-y-auto shrink-0">
        <SidebarContent {...props} />
      </div>

      {/* Mobile bottom sheet */}
      <div className="lg:hidden flex items-center gap-2 border-b border-border bg-card px-4 py-2 shrink-0">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" size="icon" className="min-h-[44px] min-w-[44px]">
              <Menu className="h-5 w-5" />
              <span className="sr-only">Open controls</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="bottom" className="max-h-[85vh] overflow-y-auto p-4 flex flex-col gap-4">
            <SheetTitle className="sr-only">Controls</SheetTitle>
            <SidebarContent {...props} />
          </SheetContent>
        </Sheet>
        {/* Quick mode tabs visible on mobile bar */}
        <Tabs value={props.mode} onValueChange={props.setMode} className="flex-1">
          <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${props.manifest.modes.length}, minmax(0, 1fr))` }}>
            {props.manifest.modes.map(m => (
              <TabsTrigger key={m.id} value={m.id} className="min-h-[44px] text-xs">
                {props.getLabel(m, 'label', props.language)}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>
    </>
  )
}
