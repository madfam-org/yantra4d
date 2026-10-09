// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManifestProvider, useManifest } from './ManifestProvider'
import fasteners from '../../../../../projects/fasteners/project.json'

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: '/project/fasteners', hash: '' }),
  useNavigate: () => vi.fn(),
}))

function ModeControls({ mode }) {
  const { ready, getParametersForMode } = useManifest()
  return <output data-testid="controls">{ready
    ? getParametersForMode(mode).map(parameter => parameter.id).sort().join(',')
    : 'loading'}</output>
}

describe('pinned fastener controls', () => {
  it.each([
    ['bolt', ['diameter', 'length', 'pitch', 'head_style_id', 'head_diameter', 'head_height', 'fn']],
    ['nut', ['diameter', 'pitch', 'nut_style_id', 'width', 'height', 'fn']],
    ['bolt_cq', ['diameter', 'length', 'pitch', 'thread_enabled', 'thread_style', 'head_style']],
    ['nut_cq', ['diameter', 'pitch', 'thread_enabled', 'thread_style', 'clearance', 'nut_style']],
    ['washer', ['diameter', 'clearance', 'washer_type']],
  ])('%s exposes controls consumed by its renderer', async (mode, expected) => {
    vi.stubGlobal('fetch', vi.fn(async url => ({
      ok: true,
      json: async () => url.endsWith('/api/projects') ? [] : fasteners,
    })))
    render(<ManifestProvider><ModeControls mode={mode} /></ManifestProvider>)
    await waitFor(() => expect(screen.getByTestId('controls')).not.toHaveTextContent('loading'))
    expect(screen.getByTestId('controls').textContent.split(',')).toEqual(expected.sort())
  })
})
