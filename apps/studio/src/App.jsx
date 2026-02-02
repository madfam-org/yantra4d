import { lazy, Suspense, useState, useCallback } from 'react'
import { Button } from "@/components/ui/button"
import { Sun, Moon, Monitor, Globe } from 'lucide-react'
import { Toaster } from "@/components/ui/sonner"
import { useAppState } from './hooks/useAppState'
import StudioHeader from './components/StudioHeader'
import StudioSidebar from './components/StudioSidebar'
import StudioMainView from './components/StudioMainView'
import ConfirmRenderDialog from './components/ConfirmRenderDialog'
import AuthButton from './components/AuthButton'
import DemoBanner from './components/DemoBanner'
import RateLimitBanner from './components/RateLimitBanner'
import { ErrorBoundary } from './components/ErrorBoundary'
import './index.css'

const ProjectsView = lazy(() => import('./components/ProjectsView'))
const OnboardingWizard = lazy(() => import('./components/OnboardingWizard'))
const ScadEditor = lazy(() => import('./components/ScadEditor'))
const GitPanel = lazy(() => import('./components/GitPanel'))
const AiChatPanel = lazy(() => import('./components/AiChatPanel'))
const ForkDialog = lazy(() => import('./components/ForkDialog'))

const isEmbed = new URLSearchParams(window.location.search).get('embed') === 'true'

function App() {
  const [editorOpen, setEditorOpen] = useState(() => sessionStorage.getItem('qubic-editor-open') === 'true')
  const toggleEditor = () => setEditorOpen(prev => {
    const next = !prev
    sessionStorage.setItem('qubic-editor-open', String(next))
    return next
  })

  const [aiPanelOpen, setAiPanelOpen] = useState(() => sessionStorage.getItem('qubic-ai-panel') === 'true')
  const toggleAiPanel = () => setAiPanelOpen(prev => {
    const next = !prev
    sessionStorage.setItem('qubic-ai-panel', String(next))
    return next
  })

  const state = useAppState()

  const [forkDialogSlug, setForkDialogSlug] = useState(null)
  const handleForkRequest = useCallback(() => setForkDialogSlug(state.projectSlug), [state.projectSlug])
  const handleForked = useCallback((newSlug) => {
    setForkDialogSlug(null)
    window.location.hash = `#/${newSlug}`
    setEditorOpen(true)
    sessionStorage.setItem('qubic-editor-open', 'true')
  }, [])
  const {
    currentView, isDemo, manifest, t, language, setLanguage, toggleLanguage, theme, cycleTheme,
    mode, setMode, getLabel, params, setParams, colors, setColors,
    wireframe, setWireframe, animating, setAnimating, presets,
    undoParams, redoParams, canUndo, canRedo,
    handleShare, shareToast,
    parts, logs, loading, progress, progressPhase,
    showConfirmDialog, pendingEstimate,
    handleGenerate, handleCancelGenerate, handleConfirmRender, handleCancelRender,
    handleVerify, handleDownloadStl, handleReset,
    handleApplyPreset, handleGridPresetToggle,
    handleExportImage, handleExportAllViews,
    exportFormat, setExportFormat,
    constraintsByParam, constraintErrors,
    printEstimate, setPrintEstimate,
    assemblyActive, highlightedParts, visibleParts,
    handleAssemblyStepChange,
    assemblyEditorOpen, setAssemblyEditorOpen,
    viewerRef, consoleRef,
  } = state

  if (!isEmbed && currentView === 'projects') {
    const ThemeIcon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor
    return (
      <div className="flex flex-col h-screen w-full bg-background text-foreground">
        <header className="h-12 border-b border-border bg-card flex items-center justify-between px-4 shrink-0">
          <h1 className="text-lg font-bold tracking-tight">Qubic</h1>
          <div className="flex items-center gap-2">
            <AuthButton />
            <Button variant="ghost" size="icon" onClick={toggleLanguage} title={language === 'es' ? t('lang.switch_to_en') : t('lang.switch_to_es')}>
              <Globe className="h-5 w-5" />
            </Button>
            <Button variant="ghost" size="icon" onClick={cycleTheme} title={t(`theme.${theme}`)}>
              <ThemeIcon className="h-5 w-5" />
            </Button>
          </div>
        </header>
        {isDemo && <DemoBanner />}
        <RateLimitBanner />
        <div className="flex-1 overflow-y-auto">
          <ErrorBoundary t={t}>
            <Suspense fallback={<div className="flex items-center justify-center h-full text-muted-foreground">Loading...</div>}>
              <ProjectsView />
            </Suspense>
          </ErrorBoundary>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen w-full bg-background text-foreground">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:text-sm focus:font-medium">
        {t('a11y.skip_to_content')}
      </a>
      {!isEmbed && (
        <StudioHeader
          manifest={manifest}
          t={t}
          language={language}
          setLanguage={setLanguage}
          theme={theme}
          cycleTheme={cycleTheme}
          undoParams={undoParams}
          redoParams={redoParams}
          canUndo={canUndo}
          canRedo={canRedo}
          handleShare={handleShare}
          shareToast={shareToast}
          editorOpen={editorOpen}
          toggleEditor={toggleEditor}
          projectSlug={state.projectSlug}
          aiPanelOpen={aiPanelOpen}
          toggleAiPanel={toggleAiPanel}
          onForkRequest={handleForkRequest}
        />
      )}

      {!isEmbed && <RateLimitBanner />}
      <div className={`flex flex-1 overflow-hidden flex-col lg:flex-row ${editorOpen ? 'editor-layout' : ''}`}>
        {editorOpen && (
          <div className="w-full lg:w-[40%] flex flex-col min-h-0 border-r border-border">
            <Suspense fallback={<div className="flex items-center justify-center h-full text-muted-foreground text-sm">Loading editor...</div>}>
              <ScadEditor slug={state.projectSlug} handleGenerate={handleGenerate} manifest={manifest} />
              <GitPanel slug={state.projectSlug} />
            </Suspense>
          </div>
        )}
        {!editorOpen && <StudioSidebar
          manifest={manifest}
          mode={mode}
          setMode={setMode}
          getLabel={getLabel}
          language={language}
          t={t}
          params={params}
          setParams={setParams}
          colors={colors}
          setColors={setColors}
          wireframe={wireframe}
          setWireframe={setWireframe}
          presets={presets}
          handleApplyPreset={handleApplyPreset}
          handleGridPresetToggle={handleGridPresetToggle}
          loading={loading}
          parts={parts}
          handleGenerate={handleGenerate}
          handleCancelGenerate={handleCancelGenerate}
          handleVerify={handleVerify}
          handleReset={handleReset}
          handleDownloadStl={handleDownloadStl}
          handleExportImage={handleExportImage}
          handleExportAllViews={handleExportAllViews}
          exportFormat={exportFormat}
          setExportFormat={setExportFormat}
          constraintsByParam={constraintsByParam}
          constraintErrors={constraintErrors}
          onAssemblyStepChange={handleAssemblyStepChange}
          assemblyEditorOpen={assemblyEditorOpen}
          setAssemblyEditorOpen={setAssemblyEditorOpen}
          viewerRef={viewerRef}
          projectSlug={state.projectSlug}
        />}

        <StudioMainView
          viewerRef={viewerRef}
          consoleRef={consoleRef}
          parts={parts}
          colors={colors}
          wireframe={wireframe}
          loading={loading}
          progress={progress}
          progressPhase={progressPhase}
          animating={animating}
          setAnimating={setAnimating}
          mode={mode}
          params={params}
          printEstimate={printEstimate}
          setPrintEstimate={setPrintEstimate}
          assemblyActive={assemblyActive}
          highlightedParts={highlightedParts}
          visibleParts={visibleParts}
          logs={logs}
          t={t}
        />
      </div>

      {/* AI Configurator overlay */}
      {aiPanelOpen && !editorOpen && (
        <div className="fixed right-0 top-12 bottom-0 w-80 z-40 border-l border-border shadow-lg">
          <Suspense fallback={<div className="flex items-center justify-center h-full text-sm text-muted-foreground">Loading AI...</div>}>
            <AiChatPanel
              mode="configurator"
              projectSlug={state.projectSlug}
              manifest={manifest}
              params={params}
              setParams={setParams}
            />
          </Suspense>
        </div>
      )}

      {/* Fork dialog */}
      {forkDialogSlug && (
        <Suspense fallback={null}>
          <ForkDialog
            slug={forkDialogSlug}
            projectName={manifest?.project?.name || forkDialogSlug}
            onClose={() => setForkDialogSlug(null)}
            onForked={handleForked}
          />
        </Suspense>
      )}

      <ConfirmRenderDialog
        open={showConfirmDialog}
        onConfirm={handleConfirmRender}
        onCancel={handleCancelRender}
        estimatedTime={pendingEstimate}
      />
      <Toaster richColors position="bottom-right" />
    </div>
  )
}

export default App
