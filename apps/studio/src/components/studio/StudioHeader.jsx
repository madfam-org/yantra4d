import { useState, useRef, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Sun, Moon, Monitor, Globe, Undo2, Redo2, Share2, Code2, Sparkles, MoreHorizontal, Ruler } from 'lucide-react'
import AuthButton from '../auth/AuthButton'
import AuthGate from '../auth/AuthGate'
import ProjectSelector from '../project/ProjectSelector'
import { SUPPORTED_LANGUAGES } from '../../config/languages'
import { useProjectMeta } from '../../hooks/project/useProjectMeta'
import { useProject } from '../../contexts/project/ProjectProvider'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useTheme } from '../../contexts/system/ThemeProvider'
import { usePlatform } from '../../contexts/system/PlatformProvider'
import { useIsMobile } from '../../hooks/system/useMediaQuery'
import { useUnitSystem } from '../../hooks/system/useUnitSystem'
import { Link } from 'react-router-dom'

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
  const isMobile = useIsMobile()
  const { unit, toggle: toggleUnit } = useUnitSystem()

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
    const keyHandler = (e) => {
      if (e.key === 'Escape') setLangOpen(false)
    }
    document.addEventListener('pointerdown', handler)
    document.addEventListener('keydown', keyHandler)
    return () => {
      document.removeEventListener('pointerdown', handler)
      document.removeEventListener('keydown', keyHandler)
    }
  }, [])

  return (
    <header className="h-12 landscape:h-11 border-b border-border bg-card flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            {!platformLoading && platformLogo !== '/logo.png' && (
              <img src={platformLogo} alt="Logo" className="h-4 w-auto rounded-sm shrink-0" onError={(e) => e.target.style.display = 'none'} />
            )}
            <h1 className="text-lg font-bold tracking-tight truncate max-w-[8rem] xs:max-w-[10rem] sm:max-w-none">{manifest.project.name}</h1>
            {manifest.project.hyperobject?.is_hyperobject && (
              <span className="hidden xs:inline-flex items-center rounded-full bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-500 ring-1 ring-inset ring-blue-500/20 shrink-0" title={`Domain: ${manifest.project.hyperobject.domain}`}>
                Commons
              </span>
            )}
          </div>
          <span className="hidden lg:block text-xs text-muted-foreground leading-tight">
            {t('platform.powered_by')} {!platformLoading ? platformName : ''}
          </span>
        </div>
        {isMobile && <Link to="/projects" className="inline-flex items-center min-h-[44px] px-1 text-xs text-muted-foreground hover:text-foreground">{t('nav.projects')}</Link>}
        {!isMobile && <ProjectSelector />}
        {!isMobile && <Link to="/projects" className="inline-flex items-center min-h-[44px] text-sm text-muted-foreground hover:text-foreground">{t('nav.projects')}</Link>}
      </div>
      <div className="flex items-center gap-1">
        <AuthButton />
        <AuthGate tier="basic">
          <Button
            variant={aiPanelOpen ? 'secondary' : 'ghost'}
            size="icon"
            className="min-h-[44px] min-w-[44px]"
            onClick={toggleAiPanel}
            title={aiPanelOpen ? t('btn.ai_close') : t('btn.ai_open')}
          >
            <Sparkles className="h-4 w-4" />
            <span className="sr-only">{aiPanelOpen ? t('btn.ai_close') : t('btn.ai_open')}</span>
          </Button>
        </AuthGate>

        {/* Desktop: show all buttons inline */}
        {!isMobile && (
          <>
            <AuthGate tier="pro">
              <Button
                variant="ghost"
                size="icon"
                className="min-h-[44px] min-w-[44px]"
                onClick={() => setSynthesisModalOpen(true)}
                title={t('btn.synthesize')}
              >
                <Sparkles className="h-4 w-4 text-purple-500" />
                <span className="sr-only">{t('btn.synthesize')}</span>
              </Button>
            </AuthGate>
            <AuthGate tier="pro">
              <Button
                variant={editorOpen ? 'secondary' : 'ghost'}
                size="icon"
                className="min-h-[44px] min-w-[44px]"
                onClick={isBuiltIn ? onForkRequest : toggleEditor}
                title={isBuiltIn ? t('btn.fork_edit') : editorOpen ? t('btn.editor_close') : t('btn.editor_open')}
              >
                <Code2 className="h-4 w-4" />
                <span className="sr-only">{editorOpen ? t('btn.editor_close') : t('btn.editor_open')}</span>
              </Button>
            </AuthGate>
            <Button variant="ghost" size="icon" className="min-h-[44px] min-w-[44px]" onClick={undoParams} disabled={!canUndo} title={t('act.undo')}>
              <Undo2 className="h-4 w-4" />
              <span className="sr-only">{t('act.undo')}</span>
            </Button>
            <Button variant="ghost" size="icon" className="min-h-[44px] min-w-[44px]" onClick={redoParams} disabled={!canRedo} title={t('act.redo')}>
              <Redo2 className="h-4 w-4" />
              <span className="sr-only">{t('act.redo')}</span>
            </Button>
            <div className="relative">
              <Button variant="ghost" size="icon" className="min-h-[44px] min-w-[44px]" onClick={handleShare} title={t('act.share')}>
                <Share2 className="h-4 w-4" />
                <span className="sr-only">{t('act.share')}</span>
              </Button>
              {shareToast && (
                <div className="absolute top-full right-0 mt-1 px-2 py-1 bg-primary text-primary-foreground text-xs rounded whitespace-nowrap max-w-[calc(100vw-2rem)] truncate z-50">
                  {t('act.share_copied')}
                </div>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="min-h-[44px] min-w-[44px] text-xs font-mono"
              onClick={toggleUnit}
              title={t('unit.toggle')}
            >
              {unit === 'mm' ? 'mm' : 'in'}
              <span className="sr-only">{t('unit.toggle')}</span>
            </Button>
            <div className="relative" ref={langRef}>
              <Button variant="ghost" size="icon" className="min-h-[44px] min-w-[44px]" onClick={() => setLangOpen(prev => !prev)} title={t('sr.toggle_lang')}>
                <Globe className="h-5 w-5" />
                <span className="sr-only">{t('sr.toggle_lang')}</span>
              </Button>
              {langOpen && (
                <div className="absolute top-full right-0 mt-1 bg-card border border-border rounded-md shadow-lg py-1 z-50 min-w-[120px] max-w-[calc(100vw-2rem)]" role="listbox" aria-expanded={langOpen}>
                  {SUPPORTED_LANGUAGES.map(lang => (
                    <button
                      key={lang.id}
                      type="button"
                      role="option"
                      aria-selected={language === lang.id}
                      className={`w-full text-left px-3 py-2.5 min-h-[44px] text-sm hover:bg-muted transition-colors ${language === lang.id ? 'font-semibold text-primary' : 'text-foreground'}`}
                      onClick={() => { setLanguage(lang.id); setLangOpen(false) }}
                    >
                      {lang.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <Button variant="ghost" size="icon" className="min-h-[44px] min-w-[44px]" onClick={cycleTheme} title={t(`theme.${theme}`)}>
              <ThemeIcon className="h-5 w-5" />
              <span className="sr-only">{t('sr.toggle_theme')}</span>
            </Button>
          </>
        )}

        {/* Mobile: overflow menu for secondary actions */}
        {isMobile && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="min-h-[44px] min-w-[44px]" title="More actions">
                <MoreHorizontal className="h-5 w-5" />
                <span className="sr-only">More actions</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-[180px]">
              <DropdownMenuItem className="min-h-[44px]" onClick={isBuiltIn ? onForkRequest : toggleEditor}>
                <Code2 className="h-4 w-4 mr-2" />
                {isBuiltIn ? t('btn.fork_edit') : editorOpen ? t('btn.editor_close') : t('btn.editor_open')}
              </DropdownMenuItem>
              <DropdownMenuItem className="min-h-[44px]" onClick={() => setSynthesisModalOpen(true)}>
                <Sparkles className="h-4 w-4 mr-2 text-purple-500" />
                {t('btn.synthesize')}
              </DropdownMenuItem>
              <DropdownMenuItem className="min-h-[44px]" onClick={undoParams} disabled={!canUndo}>
                <Undo2 className="h-4 w-4 mr-2" />
                {t('act.undo')}
              </DropdownMenuItem>
              <DropdownMenuItem className="min-h-[44px]" onClick={redoParams} disabled={!canRedo}>
                <Redo2 className="h-4 w-4 mr-2" />
                {t('act.redo')}
              </DropdownMenuItem>
              <DropdownMenuItem className="min-h-[44px]" onClick={handleShare}>
                <Share2 className="h-4 w-4 mr-2" />
                {t('act.share')}
              </DropdownMenuItem>
              <DropdownMenuItem className="min-h-[44px]" onClick={toggleUnit}>
                <Ruler className="h-4 w-4 mr-2" />
                {unit === 'mm' ? 'mm → in' : 'in → mm'}
              </DropdownMenuItem>
              <DropdownMenuItem className="min-h-[44px]" onClick={cycleTheme}>
                <ThemeIcon className="h-4 w-4 mr-2" />
                {t(`theme.${theme}`)}
              </DropdownMenuItem>
              {SUPPORTED_LANGUAGES.map(lang => (
                <DropdownMenuItem
                  key={lang.id}
                  onClick={() => setLanguage(lang.id)}
                  className={`min-h-[44px] ${language === lang.id ? 'font-semibold' : ''}`}
                >
                  <Globe className="h-4 w-4 mr-2" />
                  {lang.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </header>
  )
}
