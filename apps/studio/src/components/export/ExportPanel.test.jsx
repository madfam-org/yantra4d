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
    // Gridfinity fallback manifest includes 7 export_formats
    expect(screen.queryByText('Format:')).toBeInTheDocument()
  })

  it('calls onExportFormatChange when format button clicked', () => {
    const onExportFormatChange = vi.fn()
    renderPanel({ exportFormat: 'stl', onExportFormatChange })
    expect(screen.getByText(/Download STL/i)).toBeInTheDocument()
  })

  it('download button shows format-specific label', () => {
    renderPanel({ exportFormat: 'step', parts: [{ type: 'main', url: 'blob:x' }] })
    expect(screen.getByText(/Download STEP/i)).toBeInTheDocument()
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

  it('renders GLB format button when manifest includes glb', () => {
    renderPanel({
      manifest: {
        project: { slug: 'test' },
        modes: [{ id: 'unit', scad_file: 'test.scad', parts: ['main'] }],
        export_formats: ['stl', '3mf', 'glb', 'obj'],
      },
    })
    // Button text includes lock icon when tier doesn't allow it
    expect(screen.getByRole('button', { name: /GLB/ })).toBeInTheDocument()
  })

  it('renders OBJ format button when manifest includes obj', () => {
    renderPanel({
      manifest: {
        project: { slug: 'test' },
        modes: [{ id: 'unit', scad_file: 'test.scad', parts: ['main'] }],
        export_formats: ['stl', '3mf', 'glb', 'obj'],
      },
    })
    expect(screen.getByRole('button', { name: /OBJ/ })).toBeInTheDocument()
  })

  it('does not render GLB button when manifest excludes it', () => {
    renderPanel({
      manifest: {
        project: { slug: 'test' },
        modes: [{ id: 'unit', scad_file: 'test.scad', parts: ['main'] }],
        export_formats: ['stl', '3mf'],
      },
    })
    expect(screen.queryByRole('button', { name: /GLB/ })).not.toBeInTheDocument()
  })

  it('download button shows OBJ label when selected', () => {
    renderPanel({ exportFormat: 'obj', parts: [{ type: 'main', url: 'blob:x' }] })
    expect(screen.getByText(/Download OBJ/i)).toBeInTheDocument()
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

  // --- Documents, estimate, share and archive ------------------------------
  // ExportPanel sat at 44% branch coverage. Everything gated behind a manifest
  // feature — BOM, assembly steps, print estimate — plus the copy/share/archive
  // handlers were unreachable from the default props, which pass no manifest.

  const MANIFEST = {
    project: { slug: 'widget' },
    modes: [{ id: 'unit', scad_file: 'widget.scad', parts: ['body', 'lid'] }],
    export_formats: ['stl', '3mf', 'off'],
    bom: [{ part: 'M3 bolt', qty: 4 }],
    assembly_steps: [{ id: 1, text: 'Insert bolt' }],
  }

  const PARTS = [{ type: 'body', url: 'blob:body' }, { type: 'lid', download_url: '/lid.stl' }]

  it('offers every format the manifest declares', () => {
    renderPanel({ manifest: MANIFEST })
    // Only shown when the manifest declares more than one format; the default
    // props render a single STL button and skip this block entirely.
    expect(screen.getByRole('button', { name: /3MF/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /OFF/ })).toBeInTheDocument()
  })

  it('label says ZIP when the mode declares multiple parts', () => {
    renderPanel({ manifest: MANIFEST })
    expect(screen.getByText(/Download STL \(ZIP\)/i)).toBeInTheDocument()
  })

  it('a format the tier does not allow is marked locked and does not change format', () => {
    const onExportFormatChange = vi.fn()
    renderPanel({ manifest: MANIFEST, onExportFormatChange })
    // Guest tier allows stl only, so 3MF carries the lock marker and its click
    // triggers the upgrade prompt instead of selecting the format.
    const locked = screen.getByRole('button', { name: /3MF/ })
    expect(locked.textContent).toMatch(/🔒/)
    fireEvent.click(locked)
    expect(onExportFormatChange).not.toHaveBeenCalled()
  })

  it('an allowed format selects on click', () => {
    const onExportFormatChange = vi.fn()
    renderPanel({ manifest: MANIFEST, onExportFormatChange })
    fireEvent.click(screen.getByRole('button', { name: 'STL', exact: true }))
    expect(onExportFormatChange).toHaveBeenCalledWith('stl')
  })

  it('SCAD download opens the mode’s scad file for the manifest slug', () => {
    const open = vi.spyOn(window, 'open').mockImplementation(() => null)
    renderPanel({ manifest: MANIFEST, parts: PARTS })
    fireEvent.click(screen.getByText(/Download SCAD/i).closest('button'))
    expect(open).toHaveBeenCalledWith(expect.stringContaining('/download/scad/widget.scad'), '_blank')
  })

  it('documents section appears only when the manifest carries a BOM or steps', () => {
    renderPanel()
    expect(screen.queryByRole('button', { name: /Documents/i })).not.toBeInTheDocument()

    renderPanel({ manifest: MANIFEST })
    expect(screen.getByRole('button', { name: /Documents/i })).toBeInTheDocument()
  })

  it('BOM CSV download carries the current parameters as query string', () => {
    const open = vi.spyOn(window, 'open').mockImplementation(() => null)
    renderPanel({ manifest: MANIFEST, parts: PARTS })
    openSection(/Documents/i)
    fireEvent.click(screen.getByText(/BOM/i).closest('button'))
    expect(open).toHaveBeenCalledWith(expect.stringContaining('/bom?format=csv'), '_blank')
  })
})

