import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import StudioHeader from './StudioHeader'

// Mock dependencies
vi.mock('../../contexts/LanguageProvider', () => ({
  useLanguage: () => ({ t: (key) => key }),
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

vi.mock('../../hooks/useProjectMeta', () => ({
  useProjectMeta: () => ({ source: { type: 'github' } }),
}))

vi.mock('../../config/languages', () => ({
  SUPPORTED_LANGUAGES: [
    { id: 'en', label: 'English' },
    { id: 'es', label: 'Español' },
  ],
}))

const defaultProps = {
  manifest: { project: { name: 'Test Project' } },
  t: (key) => key,
  language: 'en',
  setLanguage: vi.fn(),
  theme: 'light',
  cycleTheme: vi.fn(),
  undoParams: vi.fn(),
  redoParams: vi.fn(),
  canUndo: false,
  canRedo: false,
  handleShare: vi.fn(),
  shareToast: false,
  editorOpen: false,
  toggleEditor: vi.fn(),
  projectSlug: 'test-project',
  aiPanelOpen: false,
  toggleAiPanel: vi.fn(),
  onForkRequest: vi.fn(),
}

beforeEach(() => {
  vi.clearAllMocks()
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
    render(<StudioHeader {...defaultProps} canUndo={false} />)
    const undoBtn = screen.getByTitle('act.undo')
    expect(undoBtn).toBeDisabled()
  })

  it('enables undo button when canUndo is true', () => {
    render(<StudioHeader {...defaultProps} canUndo={true} />)
    const undoBtn = screen.getByTitle('act.undo')
    expect(undoBtn).not.toBeDisabled()
  })

  it('calls undoParams when undo button clicked', () => {
    render(<StudioHeader {...defaultProps} canUndo={true} />)
    fireEvent.click(screen.getByTitle('act.undo'))
    expect(defaultProps.undoParams).toHaveBeenCalledOnce()
  })

  it('disables redo button when canRedo is false', () => {
    render(<StudioHeader {...defaultProps} canRedo={false} />)
    const redoBtn = screen.getByTitle('act.redo')
    expect(redoBtn).toBeDisabled()
  })

  it('enables redo and calls redoParams on click', () => {
    render(<StudioHeader {...defaultProps} canRedo={true} />)
    const redoBtn = screen.getByTitle('act.redo')
    expect(redoBtn).not.toBeDisabled()
    fireEvent.click(redoBtn)
    expect(defaultProps.redoParams).toHaveBeenCalledOnce()
  })

  it('calls handleShare when share button clicked', () => {
    render(<StudioHeader {...defaultProps} />)
    fireEvent.click(screen.getByTitle('act.share'))
    expect(defaultProps.handleShare).toHaveBeenCalledOnce()
  })

  it('shows share toast when shareToast is true', () => {
    render(<StudioHeader {...defaultProps} shareToast={true} />)
    expect(screen.getByText('act.share_copied')).toBeInTheDocument()
  })

  it('does not show share toast when shareToast is false', () => {
    render(<StudioHeader {...defaultProps} shareToast={false} />)
    expect(screen.queryByText('act.share_copied')).not.toBeInTheDocument()
  })

  it('calls cycleTheme when theme button clicked', () => {
    render(<StudioHeader {...defaultProps} />)
    fireEvent.click(screen.getByTitle('theme.light'))
    expect(defaultProps.cycleTheme).toHaveBeenCalledOnce()
  })

  it('toggles language dropdown', () => {
    render(<StudioHeader {...defaultProps} />)
    // Initially closed — no language options visible
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
    expect(defaultProps.setLanguage).toHaveBeenCalledWith('es')
  })

  it('calls toggleAiPanel when AI button clicked', () => {
    render(<StudioHeader {...defaultProps} />)
    fireEvent.click(screen.getByTitle('Open AI configurator'))
    expect(defaultProps.toggleAiPanel).toHaveBeenCalledOnce()
  })

  it('calls toggleEditor when code button clicked for non-built-in project', () => {
    render(<StudioHeader {...defaultProps} />)
    // Since useProjectMeta returns source.type='github', isBuiltIn=false
    fireEvent.click(screen.getByTitle('Open code editor'))
    expect(defaultProps.toggleEditor).toHaveBeenCalledOnce()
  })

  it('renders auth gates for AI and editor', () => {
    render(<StudioHeader {...defaultProps} />)
    expect(screen.getByTestId('auth-gate-basic')).toBeInTheDocument()
    expect(screen.getByTestId('auth-gate-pro')).toBeInTheDocument()
  })
})
