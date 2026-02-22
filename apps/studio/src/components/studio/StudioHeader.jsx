import { useState, useRef, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Sun, Moon, Monitor, Globe, Undo2, Redo2, Share2, Code2, Sparkles } from 'lucide-react'
import AuthButton from '../auth/AuthButton'
import AuthGate from '../auth/AuthGate'
import ProjectSelector from '../project/ProjectSelector'
import { SUPPORTED_LANGUAGES } from '../../config/languages'
import { useProjectMeta } from '../../hooks/project/useProjectMeta'
import { useProject } from '../../contexts/project/ProjectProvider'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useTheme } from '../../contexts/system/ThemeProvider'
import { usePlatform } from '../../contexts/system/PlatformProvider'

export default function StudioHeader({
  editorOpen, toggleEditor,
  aiPanelOpen, toggleAiPanel, onForkRequest,
  setSynthesisModalOpen
}) {
  const {
    manifest, projectSlug,
    undoParams, redoParams, canUndo, canRedo,
    handleShare, shareToast,
  } = useProject()

  const { language, setLanguage, t } = useLanguage()
  const { theme, setTheme } = useTheme()
  const { platformName, platformLogo, loading: platformLoading } = usePlatform()

  const cycleTheme = () => {
    const themes = ['light', 'dark', 'system']
    const currentIndex = themes.indexOf(theme)
    setTheme(themes[(currentIndex + 1) % themes.length])
  }

  const ThemeIcon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor
  const [langOpen, setLangOpen] = useState(false)
  const langRef = useRef(null)
  const projectMeta = useProjectMeta(projectSlug)
  const isBuiltIn = !projectMeta?.source?.type

  useEffect(() => {
    const handler = (e) => {
      if (langRef.current && !langRef.current.contains(e.target)) setLangOpen(false)
    }
    document.addEventListener('pointerdown', handler)
    return () => document.removeEventListener('pointerdown', handler)
  }, [])

  return (
    <header className="h-12 border-b border-border bg-card flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-3">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            {!platformLoading && platformLogo !== '/logo.png' && (
              <img src={platformLogo} alt="Logo" className="h-4 w-auto rounded-sm" onError={(e) => e.target.style.display = 'none'} />
            )}
            <h1 className="text-lg font-bold tracking-tight">{manifest.project.name}</h1>
            {manifest.project.hyperobject?.is_hyperobject && (
              <span className="inline-flex items-center rounded-full bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-500 ring-1 ring-inset ring-blue-500/20" title={`Domain: ${manifest.project.hyperobject.domain}`}>
                Commons
              </span>
            )}
          </div>
          <span className="text-[10px] text-muted-foreground leading-tight">
            {t('platform.powered_by')} {!platformLoading ? platformName : ''}
          </span>
        </div>
        <ProjectSelector />
        <a href="#/projects" className="text-sm text-muted-foreground hover:text-foreground">{t('nav.projects')}</a>
      </div>
      <div className="flex items-center gap-1">
        <AuthButton />
        <AuthGate tier="basic">
          <Button
            variant={aiPanelOpen ? 'secondary' : 'ghost'}
            size="icon"
            onClick={toggleAiPanel}
            title={aiPanelOpen ? 'Close AI configurator' : 'Open AI configurator'}
          >
            <Sparkles className="h-4 w-4" />
            <span className="sr-only">{aiPanelOpen ? 'Close AI configurator' : 'Open AI configurator'}</span>
          </Button>
        </AuthGate>
        <AuthGate tier="pro">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSynthesisModalOpen(true)}
            title="Synthesize Project"
          >
            <Sparkles className="h-4 w-4 text-purple-500" />
            <span className="sr-only">Synthesize Project</span>
          </Button>
        </AuthGate>
        <AuthGate tier="pro">
          <Button
            variant={editorOpen ? 'secondary' : 'ghost'}
            size="icon"
            onClick={isBuiltIn ? onForkRequest : toggleEditor}
            title={isBuiltIn ? 'Fork & edit code' : editorOpen ? 'Close code editor' : 'Open code editor'}
          >
            <Code2 className="h-4 w-4" />
            <span className="sr-only">{editorOpen ? 'Close code editor' : 'Open code editor'}</span>
          </Button>
        </AuthGate>
        <Button variant="ghost" size="icon" onClick={undoParams} disabled={!canUndo} title={t('act.undo')}>
          <Undo2 className="h-4 w-4" />
          <span className="sr-only">{t('act.undo')}</span>
        </Button>
        <Button variant="ghost" size="icon" onClick={redoParams} disabled={!canRedo} title={t('act.redo')}>
          <Redo2 className="h-4 w-4" />
          <span className="sr-only">{t('act.redo')}</span>
        </Button>
        <div className="relative">
          <Button variant="ghost" size="icon" onClick={handleShare} title={t('act.share')}>
            <Share2 className="h-4 w-4" />
            <span className="sr-only">{t('act.share')}</span>
          </Button>
          {shareToast && (
            <div className="absolute top-full right-0 mt-1 px-2 py-1 bg-primary text-primary-foreground text-xs rounded whitespace-nowrap z-50">
              {t('act.share_copied')}
            </div>
          )}
        </div>
        <div className="relative" ref={langRef}>
          <Button variant="ghost" size="icon" onClick={() => setLangOpen(prev => !prev)} title={t('sr.toggle_lang')}>
            <Globe className="h-5 w-5" />
            <span className="sr-only">{t('sr.toggle_lang')}</span>
          </Button>
          {langOpen && (
            <div className="absolute top-full right-0 mt-1 bg-card border border-border rounded-md shadow-lg py-1 z-50 min-w-[120px]">
              {SUPPORTED_LANGUAGES.map(lang => (
                <button
                  key={lang.id}
                  type="button"
                  className={`w-full text-left px-3 py-1.5 text-sm hover:bg-muted transition-colors ${language === lang.id ? 'font-semibold text-primary' : 'text-foreground'}`}
                  onClick={() => { setLanguage(lang.id); setLangOpen(false) }}
                >
                  {lang.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <Button variant="ghost" size="icon" onClick={cycleTheme} title={t(`theme.${theme}`)}>
          <ThemeIcon className="h-5 w-5" />
          <span className="sr-only">{t('sr.toggle_theme')}</span>
        </Button>
      </div>
    </header>
  )
}
