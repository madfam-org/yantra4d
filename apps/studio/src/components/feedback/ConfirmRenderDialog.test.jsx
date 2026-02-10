import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ConfirmRenderDialog from './ConfirmRenderDialog'
import { LanguageProvider } from '../../contexts/LanguageProvider'

const renderWithProviders = (ui) =>
  render(<LanguageProvider defaultLanguage="en">{ui}</LanguageProvider>)

describe('ConfirmRenderDialog', () => {
  it('renders when open=true and shows estimated time in seconds', () => {
    renderWithProviders(
      <ConfirmRenderDialog open={true} onConfirm={() => {}} onCancel={() => {}} estimatedTime={30} />
    )
    expect(screen.getByText('Long Render Warning', { exact: false })).toBeInTheDocument()
    expect(screen.getByText(/~30 seconds/)).toBeInTheDocument()
  })

  it('shows estimated time in minutes for >= 60s', () => {
    renderWithProviders(
      <ConfirmRenderDialog open={true} onConfirm={() => {}} onCancel={() => {}} estimatedTime={120} />
    )
    expect(screen.getByText(/~2 minutes/)).toBeInTheDocument()
  })

  it('calls onConfirm when confirm clicked', () => {
    const onConfirm = vi.fn()
    renderWithProviders(
      <ConfirmRenderDialog open={true} onConfirm={onConfirm} onCancel={() => {}} estimatedTime={10} />
    )
    screen.getByText('Render Anyway').click()
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('calls onCancel when cancel clicked', () => {
    const onCancel = vi.fn()
    renderWithProviders(
      <ConfirmRenderDialog open={true} onConfirm={() => {}} onCancel={onCancel} estimatedTime={10} />
    )
    screen.getByText('Cancel').click()
    expect(onCancel).toHaveBeenCalled()
  })
})
