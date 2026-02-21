import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import StudioHeader from './StudioHeader'

// Mock dependencies
vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: vi.fn(),
}))

vi.mock('../../contexts/system/ThemeProvider', () => ({
  useTheme: vi.fn(),
}))

vi.mock('../../contexts/project/ProjectProvider', () => ({
  useProject: vi.fn(),
}))

vi.mock('../auth/AuthButton', () => ({
  default: () => <div data-testid="auth-button">Auth</div>,
}))

vi.mock('../auth/AuthGate', () => ({
  default: ({ children, tier }) => <div data-testid={`auth-gate-${tier}`}>{children}</div>,
}))

vi.mock('../project/ProjectSelector', () => ({
  default: () => <div data-testid="project-selector">Projects</div>,
}))

vi.mock('../../hooks/project/useProjectMeta', () => ({
  useProjectMeta: () => ({ source: { type: 'github' } }),
}))

vi.mock('../../config/languages', () => ({
  SUPPORTED_LANGUAGES: [
    { id: 'en', label: 'English' },
    { id: 'es', label: 'Español' },
  ],
}))

import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useTheme } from '../../contexts/system/ThemeProvider'
import { useProject } from '../../contexts/project/ProjectProvider'

const baseProjectContext = {
  manifest: { project: { name: 'Test Project' } },
  undoParams: vi.fn(),
  redoParams: vi.fn(),
  canUndo: false,
  canRedo: false,
  handleShare: vi.fn(),
  shareToast: false,
  projectSlug: 'test-project',
}

const baseThemeContext = {
  theme: 'light',
  setTheme: vi.fn(),
}

const baseLanguageContext = {
  language: 'en',
  setLanguage: vi.fn(),
  t: (key) => key,
}

const defaultProps = {
  editorOpen: false,
  toggleEditor: vi.fn(),
  aiPanelOpen: false,
  toggleAiPanel: vi.fn(),
  onForkRequest: vi.fn(),
}

beforeEach(() => {
  vi.clearAllMocks()
  useProject.mockReturnValue(baseProjectContext)
  useTheme.mockReturnValue(baseThemeContext)
  useLanguage.mockReturnValue(baseLanguageContext)
})

describe('StudioHeader', () => {
  it('renders project name from manifest', () => {
    render(<StudioHeader {...defaultProps} />)
    expect(screen.getByText('Test Project')).toBeInTheDocument()
  })

  it('renders powered-by tagline', () => {
    render(<StudioHeader {...defaultProps} />)
    expect(screen.getByText('platform.powered_by')).toBeInTheDocument()
  })

  it('renders auth button and project selector', () => {
    render(<StudioHeader {...defaultProps} />)
    expect(screen.getByTestId('auth-button')).toBeInTheDocument()
    expect(screen.getByTestId('project-selector')).toBeInTheDocument()
  })

  it('renders projects link', () => {
    render(<StudioHeader {...defaultProps} />)
    expect(screen.getByText('nav.projects')).toBeInTheDocument()
  })

  it('disables undo button when canUndo is false', () => {
    useProject.mockReturnValue({ ...baseProjectContext, canUndo: false })
    render(<StudioHeader {...defaultProps} />)
    const undoBtn = screen.getByTitle('act.undo')
    expect(undoBtn).toBeDisabled()
  })

  it('enables undo button when canUndo is true', () => {
    useProject.mockReturnValue({ ...baseProjectContext, canUndo: true })
    render(<StudioHeader {...defaultProps} />)
    const undoBtn = screen.getByTitle('act.undo')
    expect(undoBtn).not.toBeDisabled()
  })

  it('calls undoParams when undo button clicked', () => {
    useProject.mockReturnValue({ ...baseProjectContext, canUndo: true })
    render(<StudioHeader {...defaultProps} />)
    fireEvent.click(screen.getByTitle('act.undo'))
    expect(baseProjectContext.undoParams).toHaveBeenCalledOnce()
  })

  it('disables redo button when canRedo is false', () => {
    useProject.mockReturnValue({ ...baseProjectContext, canRedo: false })
    render(<StudioHeader {...defaultProps} />)
    const redoBtn = screen.getByTitle('act.redo')
    expect(redoBtn).toBeDisabled()
  })

  it('enables redo and calls redoParams on click', () => {
    useProject.mockReturnValue({ ...baseProjectContext, canRedo: true })
    render(<StudioHeader {...defaultProps} />)
    const redoBtn = screen.getByTitle('act.redo')
    expect(redoBtn).not.toBeDisabled()
    fireEvent.click(redoBtn)
    expect(baseProjectContext.redoParams).toHaveBeenCalledOnce()
  })

  it('calls handleShare when share button clicked', () => {
    render(<StudioHeader {...defaultProps} />)
    fireEvent.click(screen.getByTitle('act.share'))
    expect(baseProjectContext.handleShare).toHaveBeenCalledOnce()
  })

  it('shows share toast when shareToast is true', () => {
    useProject.mockReturnValue({ ...baseProjectContext, shareToast: true })
    render(<StudioHeader {...defaultProps} />)
    expect(screen.getByText('act.share_copied')).toBeInTheDocument()
  })

  it('does not show share toast when shareToast is false', () => {
    useProject.mockReturnValue({ ...baseProjectContext, shareToast: false })
    render(<StudioHeader {...defaultProps} />)
    expect(screen.queryByText('act.share_copied')).not.toBeInTheDocument()
  })

  it('calls setTheme to cycle theme when theme button clicked', () => {
    // light -> dark
    useTheme.mockReturnValue({ ...baseThemeContext, theme: 'light' })
    render(<StudioHeader {...defaultProps} />)
    fireEvent.click(screen.getByTitle('theme.light'))
    expect(baseThemeContext.setTheme).toHaveBeenCalledWith('dark')
  })

  it('toggles language dropdown', () => {
    render(<StudioHeader {...defaultProps} />)
    // Initially closed
    expect(screen.queryByText('English')).not.toBeInTheDocument()
    // Open
    fireEvent.click(screen.getByTitle('sr.toggle_lang'))
    expect(screen.getByText('English')).toBeInTheDocument()
    expect(screen.getByText('Español')).toBeInTheDocument()
  })

  it('calls setLanguage when a language is selected', () => {
    render(<StudioHeader {...defaultProps} />)
    fireEvent.click(screen.getByTitle('sr.toggle_lang'))
    fireEvent.click(screen.getByText('Español'))
    expect(baseLanguageContext.setLanguage).toHaveBeenCalledWith('es')
  })

  it('calls toggleAiPanel when AI button clicked', () => {
    render(<StudioHeader {...defaultProps} />)
    fireEvent.click(screen.getByTitle('Open AI configurator'))
    expect(defaultProps.toggleAiPanel).toHaveBeenCalledOnce()
  })

  it('calls toggleEditor when code button clicked for non-built-in project', () => {
    render(<StudioHeader {...defaultProps} />)
    fireEvent.click(screen.getByTitle('Open code editor'))
    expect(defaultProps.toggleEditor).toHaveBeenCalledOnce()
  })

  it('renders auth gates for AI and editor', () => {
    render(<StudioHeader {...defaultProps} />)
    expect(screen.getByTestId('auth-gate-basic')).toBeInTheDocument()
    expect(screen.getByTestId('auth-gate-pro')).toBeInTheDocument()
  })
})
