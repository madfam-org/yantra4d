import { useState, useRef, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Sun, Moon, Monitor, Globe, Undo2, Redo2, Share2, Code2, Sparkles } from 'lucide-react'
import AuthButton from '../auth/AuthButton'
import AuthGate from '../auth/AuthGate'
import ProjectSelector from '../project/ProjectSelector'
import { SUPPORTED_LANGUAGES } from '../../config/languages'
import { useProjectMeta } from '../../hooks/useProjectMeta'
import { useProject } from '../../contexts/ProjectProvider'
import { useLanguage } from '../../contexts/LanguageProvider'
import { useTheme } from '../../contexts/ThemeProvider'

export default function StudioHeader({
  editorOpen, toggleEditor,
  aiPanelOpen, toggleAiPanel, onForkRequest,
}) {
  const {
    manifest, projectSlug,
    undoParams, redoParams, canUndo, canRedo,
    handleShare, shareToast,
  } = useProject()

  const { language, setLanguage, t } = useLanguage()
  const { theme, setTheme } = useTheme()

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
          <h1 className="text-lg font-bold tracking-tight">{manifest.project.name}</h1>
          <span className="text-[10px] text-muted-foreground leading-tight">{t('platform.powered_by')}</span>
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
