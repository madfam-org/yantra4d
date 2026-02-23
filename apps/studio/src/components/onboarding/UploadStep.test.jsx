import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import UploadStep from './UploadStep'

const t = (key) => {
  const map = {
    'onboard.upload_title': 'Upload SCAD Files',
    'onboard.slug_label': 'Project Slug',
    'onboard.slug_placeholder': 'my-project',
    'onboard.drop_text': 'Drop .scad files here',
    'onboard.browse': 'Browse files',
    'onboard.files_selected': 'files selected',
    'onboard.analyzing': 'Analyzing...',
    'onboard.analyze_btn': 'Analyze',
  }
  return map[key] || key
}

const defaultProps = {
  slug: 'test-project',
  setSlug: vi.fn(),
  files: [],
  handleFileDrop: vi.fn(),
  handleAnalyze: vi.fn(),
  loading: false,
  t,
}

function renderUpload(overrides = {}) {
  return render(<UploadStep {...defaultProps} {...overrides} />)
}

describe('UploadStep', () => {
  it('renders title', () => {
    renderUpload()
    expect(screen.getByText('Upload SCAD Files')).toBeInTheDocument()
  })

  it('renders slug input with current value', () => {
    renderUpload()
    expect(screen.getByDisplayValue('test-project')).toBeInTheDocument()
    expect(screen.getByText('Project Slug')).toBeInTheDocument()
  })

  it('slug input strips invalid characters', () => {
    const setSlug = vi.fn()
    renderUpload({ setSlug })
    const input = screen.getByDisplayValue('test-project')
    fireEvent.change(input, { target: { value: 'Hello World!@#' } })
    expect(setSlug).toHaveBeenCalledWith('HelloWorld')
  })

  it('renders drop zone with text', () => {
    renderUpload()
    expect(screen.getByText('Drop .scad files here')).toBeInTheDocument()
    expect(screen.getByText('Browse files')).toBeInTheDocument()
  })

  it('renders file input with .scad accept filter', () => {
    renderUpload()
    const fileInput = document.getElementById('scad-upload')
    expect(fileInput).toHaveAttribute('accept', '.scad')
    expect(fileInput).toHaveAttribute('multiple')
  })

  it('does not show file list when no files selected', () => {
    renderUpload()
    expect(screen.queryByText(/files selected/)).not.toBeInTheDocument()
  })

  it('shows file list when files are present', () => {
    const files = [{ name: 'main.scad' }, { name: 'alt.scad' }]
    renderUpload({ files })
    expect(screen.getByText('2 files selected')).toBeInTheDocument()
    expect(screen.getByText('main.scad')).toBeInTheDocument()
    expect(screen.getByText('alt.scad')).toBeInTheDocument()
  })

  it('analyze button is disabled when no files', () => {
    renderUpload()
    expect(screen.getByText('Analyze')).toBeDisabled()
  })

  it('analyze button is enabled when files are present', () => {
    renderUpload({ files: [{ name: 'test.scad' }] })
    expect(screen.getByText('Analyze')).not.toBeDisabled()
  })

  it('analyze button is disabled during loading', () => {
    renderUpload({ files: [{ name: 'test.scad' }], loading: true })
    expect(screen.getByText('Analyzing...')).toBeDisabled()
  })

  it('shows analyzing text during loading', () => {
    renderUpload({ files: [{ name: 'test.scad' }], loading: true })
    expect(screen.getByText('Analyzing...')).toBeInTheDocument()
  })

  it('clicking analyze calls handleAnalyze', () => {
    const handleAnalyze = vi.fn()
    renderUpload({ files: [{ name: 'test.scad' }], handleAnalyze })
    fireEvent.click(screen.getByText('Analyze'))
    expect(handleAnalyze).toHaveBeenCalledOnce()
  })

  it('drop zone calls handleFileDrop on drop event', () => {
    const handleFileDrop = vi.fn()
    renderUpload({ handleFileDrop })
    const dropZone = screen.getByText('Drop .scad files here').closest('div')
    fireEvent.drop(dropZone, {
      dataTransfer: { files: [new File(['content'], 'test.scad')] },
    })
    expect(handleFileDrop).toHaveBeenCalled()
  })
})
