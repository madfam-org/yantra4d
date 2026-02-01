import { lazy, Suspense } from 'react'
import { Button } from "@/components/ui/button"
import { Sun, Moon, Monitor, Globe } from 'lucide-react'
import { Toaster } from "@/components/ui/sonner"
import { useAppState } from './hooks/useAppState'
import StudioHeader from './components/StudioHeader'
import StudioSidebar from './components/StudioSidebar'
import StudioMainView from './components/StudioMainView'
import ConfirmRenderDialog from './components/ConfirmRenderDialog'
import AuthButton from './components/AuthButton'
import { ErrorBoundary } from './components/ErrorBoundary'
import './index.css'

const ProjectsView = lazy(() => import('./components/ProjectsView'))
const OnboardingWizard = lazy(() => import('./components/OnboardingWizard'))

function App() {
  const state = useAppState()
  const {
    currentView, manifest, t, language, setLanguage, toggleLanguage, theme, cycleTheme,
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
    viewerRef, consoleRef,
  } = state

  if (currentView === 'projects') {
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
      />

      <div className="flex flex-1 overflow-hidden flex-col lg:flex-row">
        <StudioSidebar
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
        />

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
          logs={logs}
          t={t}
        />
      </div>

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
