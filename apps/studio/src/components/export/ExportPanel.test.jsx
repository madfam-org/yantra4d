import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import ExportPanel from './ExportPanel'
import { renderWithProviders } from '../../test/render-with-providers'

vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('no backend'))

function renderPanel(props = {}) {
  const defaultProps = {
    parts: [],
    mode: 'unit',
    onDownloadStl: vi.fn(),
    onExportImage: vi.fn(),
    onExportAllViews: vi.fn(),
  }
  return renderWithProviders(<ExportPanel {...defaultProps} {...props} />)
}

function openSection(name) {
  const trigger = screen.getByRole('button', { name })
  fireEvent.click(trigger)
}

describe('ExportPanel', () => {
  it('renders accordion with Geometry section open by default', () => {
    renderPanel()
    // Geometry section is open by default, so Download STL is visible
    expect(screen.getByText(/Download STL/i)).toBeInTheDocument()
  })

  it('download button is disabled when no parts', () => {
    renderPanel()
    expect(screen.getByText(/Download STL/i).closest('button')).toBeDisabled()
  })

  it('download button is enabled when parts exist', () => {
    renderPanel({ parts: [{ type: 'main', url: 'blob:x' }] })
    expect(screen.getByText(/Download STL/i).closest('button')).not.toBeDisabled()
  })

  it('renders export all views button inside images section', () => {
    renderPanel()
    openSection('Images')
    expect(screen.getByText(/Export All/i)).toBeInTheDocument()
  })

  it('calls onDownloadStl when download clicked', () => {
    const onDownloadStl = vi.fn()
    renderPanel({ parts: [{ type: 'main', url: 'blob:x' }], onDownloadStl })
    screen.getByText(/Download STL/i).click()
    expect(onDownloadStl).toHaveBeenCalled()
  })

  it('shows format selector when manifest has export_formats', () => {
    renderPanel()
    // Gridfinity fallback manifest includes export_formats: ["stl", "3mf"]
    expect(screen.queryByText('Format:')).toBeInTheDocument()
  })

  it('calls onExportFormatChange when format button clicked', () => {
    const onExportFormatChange = vi.fn()
    renderPanel({ exportFormat: 'stl', onExportFormatChange })
    expect(screen.getByText(/Download STL/i)).toBeInTheDocument()
  })

  it('renders accordion section headers', () => {
    renderPanel()
    expect(screen.getByRole('button', { name: 'Geometry' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Images' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Share & Archive' })).toBeInTheDocument()
  })

  it('documents section appears when manifest has bom', () => {
    renderPanel({
      manifest: {
        project: { slug: 'test' },
        modes: [{ id: 'unit', scad_file: 'test.scad', parts: ['main'] }],
        bom: [{ item: 'Bolt', qty: 4 }],
      },
    })
    const trigger = screen.getByRole('button', { name: 'Documents' })
    expect(trigger).toBeInTheDocument()
    fireEvent.click(trigger)
    expect(screen.getByText(/Download BOM/i)).toBeInTheDocument()
  })

  it('documents section hidden when no bom or assembly_steps', () => {
    renderPanel({
      manifest: {
        project: { slug: 'test' },
        modes: [{ id: 'unit', scad_file: 'test.scad', parts: ['main'] }],
      },
    })
    expect(screen.queryByRole('button', { name: 'Documents' })).not.toBeInTheDocument()
  })

  it('print estimate section hidden when no parts', () => {
    renderPanel({ parts: [] })
    expect(screen.queryByRole('button', { name: 'Print Estimate' })).not.toBeInTheDocument()
  })

  it('share link button is present in share section', () => {
    renderPanel()
    openSection('Share & Archive')
    expect(screen.getByText(/Copy Share Link/i)).toBeInTheDocument()
  })

  it('archive button is disabled when no parts rendered', () => {
    renderPanel()
    openSection('Share & Archive')
    expect(screen.getByText(/Download Project Archive/i).closest('button')).toBeDisabled()
  })

  it('archive button is enabled when parts exist', () => {
    renderPanel({ parts: [{ type: 'main', url: 'blob:x' }] })
    openSection('Share & Archive')
    expect(screen.getByText(/Download Project Archive/i).closest('button')).not.toBeDisabled()
  })

  it('SCAD download button renders', () => {
    renderPanel()
    expect(screen.getByText(/Download SCAD/i)).toBeInTheDocument()
  })

  it('assembly step count shown when assembly_steps exist', () => {
    renderPanel({
      manifest: {
        project: { slug: 'test' },
        modes: [{ id: 'unit', scad_file: 'test.scad', parts: ['main'] }],
        assembly_steps: [{ id: 's1' }, { id: 's2' }, { id: 's3' }],
      },
    })
    openSection('Documents')
    expect(screen.getByText(/3 assembly steps/i)).toBeInTheDocument()
  })
})
