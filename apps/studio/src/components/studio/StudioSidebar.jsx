import { useState } from 'react'
import Controls from '../controls/Controls'
import ExportPanel from '../export/ExportPanel'
import BomPanel from '../bom/BomPanel'
import AppearancePanel from '../controls/AppearancePanel'
import AssemblyView from '../bom/AssemblyView'
import AssemblyEditorPanel from '../assembly-editor/AssemblyEditorPanel'
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { Square, RotateCcw, Menu, Wrench, Settings2, AreaChart, Download, Sparkles, CheckCircle2 } from 'lucide-react'
import { useProject } from '../../contexts/project/ProjectProvider'
import { useLanguage } from '../../contexts/system/LanguageProvider'

function ActionDock() {
  const { loading, constraintErrors, parts, handleGenerate, handleCancelGenerate, handleVerify, handleReset } = useProject()
  const { t } = useLanguage()

  return (
    <div className="absolute bottom-0 left-0 right-0 p-4 bg-background/85 backdrop-blur-xl border-t border-border flex flex-col gap-2 z-20 shadow-[0_-4px_24px_rgba(0,0,0,0.05)] dark:shadow-[0_-4px_24px_rgba(0,0,0,0.2)]">
      <Button
        type="button"
        onClick={() => handleGenerate()}
        disabled={loading || constraintErrors}
        className="w-full h-11 shadow-sm font-medium transition-all"
        title={t("tooltip.gen")}
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <span className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
            {t("btn.proc")}
          </span>
        ) : (
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            {t("btn.gen")}
          </span>
        )}
      </Button>

      <div className="grid grid-cols-2 gap-2 text-xs">
        {loading ? (
          <Button variant="destructive" onClick={handleCancelGenerate} className="w-full gap-1.5 h-9 text-xs">
            <Square className="h-3.5 w-3.5" />
            {t("btn.cancel")}
          </Button>
        ) : (
          <Button
            variant="outline"
            onClick={() => handleGenerate(true)}
            disabled={constraintErrors}
            className="w-full h-9 text-xs"
            title={t("tooltip.force_gen")}
          >
            {t("btn.force_gen")}
          </Button>
        )}

        <div className="flex gap-2">
          <Button
            variant="secondary"
            onClick={handleVerify}
            disabled={loading || parts.length === 0}
            className="flex-1 h-9 text-xs gap-1.5"
            title={t("tooltip.verify")}
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span className="sr-only sm:not-sr-only">{t("btn.verify")}</span>
          </Button>
          <Button variant="outline" size="icon" onClick={handleReset} className="h-9 w-9 shrink-0" title={t("btn.reset")}>
            <RotateCcw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  )
}

function SidebarContent() {
  const {
    manifest, mode, setMode, getLabel,
    params, setParams, colors, setColors,
    wireframe, setWireframe, boundingBox, setBoundingBox,
    presets, handleApplyPreset, handleGridPresetToggle,
    parts,
    exportFormat, setExportFormat,
    handleDownloadStl, handleExportImage, handleExportAllViews,
    constraintsByParam,
    handleAssemblyStepChange,
    assemblyEditorOpen, setAssemblyEditorOpen,
    viewerRef, projectSlug,
    clippingEnabled, setClippingEnabled,
    clippingAxis, setClippingAxis,
    clippingPosition, setClippingPosition,
    measureMode, setMeasureMode,
    measurements, setMeasurements,
    explodeFactor, setExplodeFactor,
    lightIntensity, setLightIntensity,
    environmentPreset, setEnvironmentPreset,
    overhangEnabled, setOverhangEnabled,
    overhangThreshold, setOverhangThreshold,
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
  const currentModeParts = manifest.modes?.find(m => m.id === mode)?.parts || []
  const showAssemblyGuide = hasAssemblySteps && manifest.assembly_steps.some(s =>
    (s.visible_parts || []).some(p => currentModeParts.includes(p))
  )

  return (
    <Tabs defaultValue="config" className="w-full flex-1 flex flex-col h-full overflow-hidden relative">
      <div className="px-4 pt-4 pb-2 bg-background z-10">
        <TabsList className="grid w-full grid-cols-4 h-11 bg-muted/60">
          <TabsTrigger value="config" className="flex items-center gap-2 text-xs">
            <Settings2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Design</span>
          </TabsTrigger>
          <TabsTrigger value="view" className="flex items-center gap-2 text-xs">
            <AreaChart className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">View</span>
          </TabsTrigger>
          <TabsTrigger value="analysis" className="flex items-center gap-2 text-xs">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">BOM</span>
          </TabsTrigger>
          <TabsTrigger value="export" className="flex items-center gap-2 text-xs">
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Export</span>
          </TabsTrigger>
        </TabsList>
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar px-4 pb-32">
        <TabsContent value="config" className="m-0 space-y-5 animate-in fade-in-50 duration-300">

          <Tabs value={mode} onValueChange={setMode} className="w-full sticky top-0 z-20 bg-background/95 backdrop-blur py-2">
            <TabsList className="grid w-full h-auto min-h-10 bg-transparent gap-1" style={{ gridTemplateColumns: `repeat(${manifest.modes.length}, minmax(0, 1fr))` }}>
              {manifest.modes.map(m => (
                <TabsTrigger
                  key={m.id}
                  value={m.id}
                  className="data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:shadow-none border border-transparent data-[state=active]:border-primary/20 min-h-[40px] whitespace-normal break-words leading-tight flex items-center justify-center gap-1.5 px-2 py-1.5 text-xs rounded-md transition-all"
                >
                  {m.svg ? (
                    <>
                      <span className="flex items-center justify-center opacity-70" dangerouslySetInnerHTML={{ __html: m.svg }} />
                      <span className="hidden md:inline-block font-medium">{getLabel(m, 'label', language)}</span>
                    </>
                  ) : (
                    <span className="font-medium">{getLabel(m, 'label', language)}</span>
                  )}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          <div className="pb-4">
            <Controls
              params={params}
              setParams={setParams}
              mode={mode}
              colors={colors}
              setColors={setColors}
              wireframe={wireframe}
              setWireframe={setWireframe}
              boundingBox={boundingBox}
              setBoundingBox={setBoundingBox}
              presets={presets}
              onApplyPreset={handleApplyPreset}
              onToggleGridPreset={handleGridPresetToggle}
              constraintsByParam={constraintsByParam}
              clippingEnabled={clippingEnabled}
              setClippingEnabled={setClippingEnabled}
              clippingAxis={clippingAxis}
              setClippingAxis={setClippingAxis}
              clippingPosition={clippingPosition}
              setClippingPosition={setClippingPosition}
              measureMode={measureMode}
              setMeasureMode={setMeasureMode}
              measurements={measurements}
              setMeasurements={setMeasurements}
              explodeFactor={explodeFactor}
              setExplodeFactor={setExplodeFactor}
              lightIntensity={lightIntensity}
              setLightIntensity={setLightIntensity}
              environmentPreset={environmentPreset}
              setEnvironmentPreset={setEnvironmentPreset}
              partsCount={parts.length}
              overhangEnabled={overhangEnabled}
              setOverhangEnabled={setOverhangEnabled}
              overhangThreshold={overhangThreshold}
              setOverhangThreshold={setOverhangThreshold}
            />
          </div>
        </TabsContent>

        <TabsContent value="view" className="m-0 space-y-4 animate-in fade-in-50 duration-300">
          <AppearancePanel
            mode={mode}
            colors={colors}
            setColors={setColors}
            wireframe={wireframe}
            setWireframe={setWireframe}
            boundingBox={boundingBox}
            setBoundingBox={setBoundingBox}
            clippingEnabled={clippingEnabled}
            setClippingEnabled={setClippingEnabled}
            clippingAxis={clippingAxis}
            setClippingAxis={setClippingAxis}
            clippingPosition={clippingPosition}
            setClippingPosition={setClippingPosition}
            measureMode={measureMode}
            setMeasureMode={setMeasureMode}
            measurements={measurements}
            setMeasurements={setMeasurements}
            explodeFactor={explodeFactor}
            setExplodeFactor={setExplodeFactor}
            lightIntensity={lightIntensity}
            setLightIntensity={setLightIntensity}
            environmentPreset={environmentPreset}
            setEnvironmentPreset={setEnvironmentPreset}
            partsCount={parts.length}
            overhangEnabled={overhangEnabled}
            setOverhangEnabled={setOverhangEnabled}
            overhangThreshold={overhangThreshold}
            setOverhangThreshold={setOverhangThreshold}
          />
        </TabsContent>

        <TabsContent value="analysis" className="m-0 space-y-4 animate-in fade-in-50 duration-300">
          <BomPanel params={params} mode={mode} />
          {showAssemblyGuide && <AssemblyView onStepChange={handleAssemblyStepChange} />}

          {/* Assembly editor toggle */}
          {(hasAssemblySteps || mode === 'assembly') && (
            <Button
              variant="outline"
              size="sm"
              className="w-full gap-2 text-xs mt-4"
              onClick={() => setAssemblyEditorOpen(true)}
            >
              <Wrench className="h-3.5 w-3.5" />
              {t('btn.edit_assembly')}
            </Button>
          )}
        </TabsContent>

        <TabsContent value="export" className="m-0 animate-in fade-in-50 duration-300">
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
        </TabsContent>
      </div>

      <ActionDock />
    </Tabs>
  )
}

export default function StudioSidebar() {
  const [open, setOpen] = useState(false)
  const { manifest, mode, setMode, getLabel } = useProject()
  const { language, t } = useLanguage()

  return (
    <>
      {/* Desktop sidebar */}
      <div data-testid="studio-sidebar" className="hidden lg:flex w-full h-full min-w-[22rem] bg-card flex-col shrink-0 relative">
        <SidebarContent />
      </div>

      {/* Mobile bottom sheet */}
      <div className="lg:hidden flex items-center gap-2 border-b border-border bg-card px-4 py-2 landscape:py-1 shrink-0">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" size="icon" className="min-h-[44px] min-w-[44px]">
              <Menu className="h-5 w-5" />
              <span className="sr-only">{t('btn.open_controls')}</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="bottom" className="max-h-[85vh] landscape:max-h-[75vh] p-0 flex flex-col">
            <div className="mx-auto mt-3 mb-2 h-1 w-10 rounded-full bg-muted-foreground/30 shrink-0" aria-hidden="true" />
            <SheetTitle className="sr-only">Controls</SheetTitle>
            <SheetDescription className="sr-only">
              {t('a11y.controls_description')}
            </SheetDescription>
            <div className="flex-1 overflow-hidden relative h-full">
              <SidebarContent />
            </div>
          </SheetContent>
        </Sheet>
        {/* Quick mode tabs visible on mobile bar */}
        <Tabs value={mode} onValueChange={setMode} className="flex-1">
          <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${manifest.modes.length}, minmax(0, 1fr))` }}>
            {manifest.modes.map(m => (
              <TabsTrigger key={m.id} value={m.id} className="min-h-[44px] text-xs" title={getLabel(m, 'label', language)}>
                {getLabel(m, 'label', language)}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>
    </>
  )
}
