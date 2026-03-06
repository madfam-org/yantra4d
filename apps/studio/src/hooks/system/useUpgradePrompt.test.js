import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import React from 'react'
import { UpgradePromptContext } from '../../contexts/auth/UpgradePromptContext'
import { useUpgradePrompt } from './useUpgradePrompt'

describe('useUpgradePrompt', () => {
  it('returns default context value when used without provider', () => {
    const { result } = renderHook(() => useUpgradePrompt())
    expect(result.current.triggerUpgradePrompt).toBeTypeOf('function')
    expect(result.current.closeUpgradePrompt).toBeTypeOf('function')
  })

  it('returns provided context value when wrapped in provider', () => {
    const trigger = vi.fn()
    const close = vi.fn()
    const wrapper = ({ children }) =>
      React.createElement(
        UpgradePromptContext.Provider,
        { value: { triggerUpgradePrompt: trigger, closeUpgradePrompt: close } },
        children
      )

    const { result } = renderHook(() => useUpgradePrompt(), { wrapper })
    expect(result.current.triggerUpgradePrompt).toBe(trigger)
    expect(result.current.closeUpgradePrompt).toBe(close)

    result.current.triggerUpgradePrompt()
    expect(trigger).toHaveBeenCalledOnce()

    result.current.closeUpgradePrompt()
    expect(close).toHaveBeenCalledOnce()
  })
})
