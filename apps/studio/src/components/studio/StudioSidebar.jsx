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
import { Square, RotateCcw, Menu, Wrench, Settings2, AreaChart, Download, Sparkles, CheckCircle2, Copy, PanelLeftClose } from 'lucide-react'
import { useProject } from '../../contexts/project/ProjectProvider'
import { useLanguage } from '../../contexts/system/LanguageProvider'

function ActionDock({ compareMode, onToggleCompare }) {
  const { loading, constraintErrors, parts, handleGenerate, handleCancelGenerate, handleVerify, handleReset } = useProject()
  const { t } = useLanguage()

  return (
    <div className="p-4 bg-background/85 backdrop-blur-xl border-t border-border flex flex-col gap-2 z-20 shadow-[0_-4px_24px_rgba(0,0,0,0.05)] dark:shadow-[0_-4px_24px_rgba(0,0,0,0.2)] shrink-0">
      {onToggleCompare && (
        <Button
          variant={compareMode ? "default" : "outline"}
          size="sm"
          onClick={onToggleCompare}
          className="w-full gap-1.5 h-9 text-xs"
        >
          <Copy className="h-3.5 w-3.5" />
          {compareMode ? t('btn.exit_compare') : t('btn.compare')}
        </Button>
      )}
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

function ModeTabs({ className }) {
  const { manifest, mode, setMode, getLabel } = useProject()
  const { language } = useLanguage()

  if (!manifest.modes || manifest.modes.length <= 1) return null

  return (
    <div className={`w-full mt-2 ${className || ''}`} role="tablist" aria-label="Mode selection">
      <div
        className="grid w-full h-auto min-h-10 bg-transparent gap-1 rounded-md p-1"
        style={{ gridTemplateColumns: `repeat(${manifest.modes.length}, minmax(0, 1fr))` }}
      >
        {manifest.modes.map(m => (
          <button
            key={m.id}
            role="tab"
            aria-selected={mode === m.id}
            onClick={() => setMode(m.id)}
            className={`min-h-[40px] whitespace-normal break-words leading-tight flex items-center justify-center gap-1.5 px-2 py-1.5 text-xs rounded-md transition-all border ${
              mode === m.id
                ? 'bg-primary/10 text-primary border-primary/20'
                : 'border-transparent text-muted-foreground hover:bg-muted/50'
            }`}
          >
            {m.svg ? (
              <>
                <span className="flex items-center justify-center opacity-70" dangerouslySetInnerHTML={{ __html: m.svg }} />
                <span className="hidden md:inline-block font-medium">{getLabel(m, 'label', language)}</span>
              </>
            ) : (
              <span className="font-medium">{getLabel(m, 'label', language)}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

function SidebarContent({ compareMode, onToggleCompare }) {
  const {
    manifest, mode,
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
    setHoveredParamId,
  } = useProject()

  const { t } = useLanguage()

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
    <Tabs defaultValue="config" className="w-full flex-1 flex flex-col min-h-0 overflow-hidden relative">
      <div className="px-4 pt-4 pb-2 bg-background/95 backdrop-blur z-20">
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
        <ModeTabs className="hidden lg:block" />
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin px-4 pb-6 min-h-0">
        <TabsContent value="config" className="m-0 space-y-5 animate-in fade-in-50 duration-300">
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
              onParamHover={setHoveredParamId}
              onParamLeave={() => setHoveredParamId(null)}
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

      <ActionDock compareMode={compareMode} onToggleCompare={onToggleCompare} />
    </Tabs>
  )
}

export default function StudioSidebar({ compareMode, onToggleCompare, variant, onCollapse }) {
  const [open, setOpen] = useState(false)
  const { manifest, mode, setMode, getLabel } = useProject()
  const { language, t } = useLanguage()

  return (
    <>
      {/* Desktop sidebar — render when variant is 'desktop' or undefined */}
      {variant !== 'mobile' && (
        <div className={`${variant === 'desktop' ? 'flex' : 'hidden lg:flex'} flex-col flex-1 min-w-0 bg-card border-r border-border overflow-y-auto overflow-x-hidden min-h-0`}>
          {onCollapse && (
            <button
              onClick={onCollapse}
              className="absolute top-2 right-2 z-30 p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
              aria-label="Collapse sidebar"
              aria-expanded={true}
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
          <div data-testid="studio-sidebar" className="w-full h-full min-w-0 flex flex-col relative">
            <SidebarContent compareMode={compareMode} onToggleCompare={onToggleCompare} />
          </div>
        </div>
      )}

      {/* Mobile bottom bar with sheet trigger + mode tabs — render when variant is 'mobile' or undefined */}
      {variant !== 'desktop' && (
        <div className={`${variant === 'mobile' ? 'flex' : 'lg:hidden flex'} items-center gap-2 border-b border-border bg-card px-4 py-2 landscape:py-1 shrink-0`}>
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" size="icon" className="min-h-[44px] min-w-[44px]">
                <Menu className="h-5 w-5" />
                <span className="sr-only">{t('btn.open_controls')}</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="bottom" className="max-h-[90dvh] landscape:max-h-[75dvh] p-0 flex flex-col gap-0 pb-safe">
              <div className="mx-auto mt-3 mb-2 h-1 w-10 rounded-full bg-muted-foreground/30 shrink-0" aria-hidden="true" />
              <SheetTitle className="sr-only">Controls</SheetTitle>
              <SheetDescription className="sr-only">
                {t('a11y.controls_description')}
              </SheetDescription>
              <div className="flex-1 min-h-0 relative flex flex-col">
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
      )}
    </>
  )
}
