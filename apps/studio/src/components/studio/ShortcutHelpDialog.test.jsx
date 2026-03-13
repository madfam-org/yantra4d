import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({ t: (key) => key }),
}))

import ShortcutHelpDialog from './ShortcutHelpDialog'

describe('ShortcutHelpDialog', () => {
  it('renders nothing when closed', () => {
    const { container } = render(<ShortcutHelpDialog open={false} onClose={vi.fn()} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders dialog with title when open', () => {
    render(<ShortcutHelpDialog open={true} onClose={vi.fn()} />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('shortcuts.title')).toBeInTheDocument()
  })

  it('renders all shortcut groups', () => {
    render(<ShortcutHelpDialog open={true} onClose={vi.fn()} />)
    expect(screen.getByText('shortcuts.viewer')).toBeInTheDocument()
    expect(screen.getByText('shortcuts.editing')).toBeInTheDocument()
    expect(screen.getByText('shortcuts.rendering')).toBeInTheDocument()
    expect(screen.getByText('shortcuts.panels')).toBeInTheDocument()
    expect(screen.getByText('shortcuts.navigation')).toBeInTheDocument()
  })

  it('renders individual shortcut labels', () => {
    render(<ShortcutHelpDialog open={true} onClose={vi.fn()} />)
    expect(screen.getByText('shortcuts.ortho')).toBeInTheDocument()
    expect(screen.getByText('shortcuts.undo')).toBeInTheDocument()
    expect(screen.getByText('shortcuts.render')).toBeInTheDocument()
    expect(screen.getByText('shortcuts.toggle_sidebar')).toBeInTheDocument()
    expect(screen.getByText('shortcuts.toggle_console')).toBeInTheDocument()
    expect(screen.getByText('shortcuts.help')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn()
    render(<ShortcutHelpDialog open={true} onClose={onClose} />)
    fireEvent.click(screen.getByLabelText('Close'))
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when backdrop is clicked', () => {
    const onClose = vi.fn()
    render(<ShortcutHelpDialog open={true} onClose={onClose} />)
    // The outer overlay uses onMouseDown={onClose}; the dialog stops propagation.
    const backdrop = screen.getByRole('dialog').parentElement
    fireEvent.mouseDown(backdrop)
    expect(onClose).toHaveBeenCalled()
  })

  it('does not call onClose when dialog content is clicked', () => {
    const onClose = vi.fn()
    render(<ShortcutHelpDialog open={true} onClose={onClose} />)
    fireEvent.click(screen.getByRole('dialog'))
    expect(onClose).not.toHaveBeenCalled()
  })
})
