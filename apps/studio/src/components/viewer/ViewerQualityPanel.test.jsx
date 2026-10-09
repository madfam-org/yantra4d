import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'

vi.mock('../../contexts/system/LanguageProvider', () => ({ useLanguage: () => ({ language: 'en', t: (key) => key }) }))

import ViewerQualityPanel from './ViewerQualityPanel'
import { getQualityMode, getQualityReadings, publishReadings, setQualityMode } from '../../lib/viewerQuality'

describe('<ViewerQualityPanel>', () => {
  it('switches the quality mode and shows the live readings', () => {
    act(() => setQualityMode('auto'))
    render(<ViewerQualityPanel />)
    expect(screen.getAllByText('viewer.quality.unavailable')).toHaveLength(2)
    expect(screen.getByText('viewer.quality.idle')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('viewer.quality.title'), { target: { value: 'battery' } })
    expect(getQualityMode()).toBe('battery')
    act(() => publishReadings({ ...getQualityReadings(), gpu: 'Test GPU', browser: 'Chrome 152', timerQuery: true, scale: 0.7, gpuMsP50: 3.24, gpuMsP90: 5, fps: 60, drawCalls: 51, triangles: 99328 }))
    expect(screen.getByText('Test GPU')).toBeInTheDocument()
    expect(screen.getByText('70%')).toBeInTheDocument()
    expect(screen.getByText('3.2 / 5.0 ms')).toBeInTheDocument()
    expect(screen.getByText('60')).toBeInTheDocument()
    expect(screen.getByTestId('viewer-quality').dataset.gpuMsP90).toBe('5')
    act(() => setQualityMode('auto'))
  })
})
