interface Language {
  id: string
  label: string
}

export const SUPPORTED_LANGUAGES: readonly Language[] = [
  { id: 'en', label: 'English' },
  { id: 'es', label: 'Español' },
  { id: 'pt', label: 'Português' },
  { id: 'fr', label: 'Français' },
  { id: 'de', label: 'Deutsch' },
  { id: 'zh', label: '中文' },
] as const
