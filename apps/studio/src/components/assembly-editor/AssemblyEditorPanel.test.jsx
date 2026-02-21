import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('../../hooks/editor/useAssemblyEditor', () => ({
  useAssemblyEditor: () => ({
    steps: [
      { step: 1, label: { en: 'Step 1' }, notes: { en: '' }, visible_parts: ['bottom'], highlight_parts: [] },
    ],
    selectedIndex: 0,
    selectedStep: { step: 1, label: { en: 'Step 1' }, notes: { en: '' }, visible_parts: ['bottom'], highlight_parts: [] },
    isDirty: false,
    saving: false,
    selectStep: vi.fn(),
    addStep: vi.fn(),
    removeStep: vi.fn(),
    updateStep: vi.fn(),
    reorderStep: vi.fn(),
    captureCamera: vi.fn(),
    save: vi.fn(),
    discard: vi.fn(),
  }),
}))

vi.mock('../../contexts/system/LanguageProvider', () => ({
  useLanguage: () => ({ language: 'en', t: (k) => k }),
}))

vi.mock('../../contexts/project/ManifestProvider', () => ({
  useManifest: () => ({
    manifest: {
      parts: [{ id: 'bottom' }, { id: 'top' }],
    },
  }),
}))

import AssemblyEditorPanel from './AssemblyEditorPanel'

describe('AssemblyEditorPanel', () => {
  it('renders with title and step list', () => {
    render(
      <AssemblyEditorPanel
        onStepChange={vi.fn()}
        onClose={vi.fn()}
        viewerRef={{ current: null }}
        projectSlug="test"
      />
    )
    expect(screen.getByText('Assembly Editor')).toBeInTheDocument()
    expect(screen.getByText('Step 1')).toBeInTheDocument()
    expect(screen.getByText('Capture Camera Position')).toBeInTheDocument()
    expect(screen.getByText('Save')).toBeInTheDocument()
  })
})
