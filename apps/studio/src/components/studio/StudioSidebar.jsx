import { useState } from 'react'
import Controls from '../Controls'
import ExportPanel from '../export/ExportPanel'
import BomPanel from '../bom/BomPanel'
import AssemblyView from '../bom/AssemblyView'
import AssemblyEditorPanel from '../assembly-editor/AssemblyEditorPanel'
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet"
import { Square, RotateCcw, Menu, Wrench } from 'lucide-react'
import { useProject } from '../../contexts/ProjectProvider'
import { useLanguage } from '../../contexts/LanguageProvider'

function SidebarContent() {
  const {
    manifest, mode, setMode, getLabel,
    params, setParams, colors, setColors, wireframe, setWireframe,
    presets, handleApplyPreset, handleGridPresetToggle,
    loading, parts,
    handleGenerate, handleCancelGenerate, handleVerify, handleReset,
    handleDownloadStl, handleExportImage, handleExportAllViews,
    exportFormat, setExportFormat,
    constraintsByParam, constraintErrors,
    handleAssemblyStepChange,
    assemblyEditorOpen, setAssemblyEditorOpen,
    viewerRef, projectSlug,
  } = useProject()

  const { language, t } = useLanguage()

  // Show editor panel instead of normal sidebar
  if (assemblyEditorOpen) {
    return (
      <AssemblyEditorPanel
        onStepChange={handleAssemblyStepChange}
        onClose={() => setAssemblyEditorOpen(false)}
        viewerRef={viewerRef}
        projectSlug={projectSlug}
      />
    )
  }

  const hasAssemblySteps = manifest?.assembly_steps?.length > 0

  // Only show assembly guide when current mode's parts overlap with assembly step parts
  const currentModeParts = manifest.modes?.find(m => m.id === mode)?.parts || []
  const showAssemblyGuide = hasAssemblySteps && manifest.assembly_steps.some(s =>
    (s.visible_parts || []).some(p => currentModeParts.includes(p))
  )

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

      <div className="hidden lg:block flex-1"></div>

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
        manifest={manifest}
        parts={parts}
        mode={mode}
        onDownloadStl={handleDownloadStl}
        onExportImage={handleExportImage}
        onExportAllViews={handleExportAllViews}
        exportFormat={exportFormat}
        onExportFormatChange={setExportFormat}
      />

      <BomPanel params={params} />
      {showAssemblyGuide && <AssemblyView onStepChange={handleAssemblyStepChange} />}

      {/* Assembly editor toggle */}
      {(hasAssemblySteps || mode === 'assembly') && (
        <Button
          variant="outline"
          size="sm"
          className="w-full gap-2 text-xs"
          onClick={() => setAssemblyEditorOpen(true)}
        >
          <Wrench className="h-3 w-3" />
          Edit Assembly Guide
        </Button>
      )}
    </>
  )
}

export default function StudioSidebar() {
  const [open, setOpen] = useState(false)
  const { manifest, mode, setMode, getLabel } = useProject()
  const { language } = useLanguage()

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden lg:flex w-80 min-w-[20rem] border-r border-border bg-card p-4 flex-col gap-4 overflow-y-auto shrink-0">
        <SidebarContent />
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
            <SidebarContent />
          </SheetContent>
        </Sheet>
        {/* Quick mode tabs visible on mobile bar */}
        <Tabs value={mode} onValueChange={setMode} className="flex-1">
          <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${manifest.modes.length}, minmax(0, 1fr))` }}>
            {manifest.modes.map(m => (
              <TabsTrigger key={m.id} value={m.id} className="min-h-[44px] text-xs">
                {getLabel(m, 'label', language)}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>
    </>
  )
}
