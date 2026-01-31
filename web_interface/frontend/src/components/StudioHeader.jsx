import { Button } from "@/components/ui/button"
import { Sun, Moon, Monitor, Globe, Undo2, Redo2, Share2 } from 'lucide-react'
import AuthButton from './AuthButton'
import ProjectSelector from './ProjectSelector'

export default function StudioHeader({
  manifest, t, language, toggleLanguage, theme, cycleTheme,
  undoParams, redoParams, canUndo, canRedo,
  handleShare, shareToast,
}) {
  const ThemeIcon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor

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
        <Button variant="ghost" size="icon" onClick={toggleLanguage} title={language === 'es' ? t('lang.switch_to_en') : t('lang.switch_to_es')}>
          <Globe className="h-5 w-5" />
          <span className="sr-only">{t('sr.toggle_lang')}</span>
        </Button>
        <Button variant="ghost" size="icon" onClick={cycleTheme} title={t(`theme.${theme}`)}>
          <ThemeIcon className="h-5 w-5" />
          <span className="sr-only">{t('sr.toggle_theme')}</span>
        </Button>
      </div>
    </header>
  )
}
