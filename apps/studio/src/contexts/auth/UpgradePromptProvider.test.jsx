import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useContext } from 'react'

// The dialog itself has its own spec; here it is a probe that surfaces the
// feature string the provider passes down.
vi.mock('../../components/auth/UpgradeDialog', () => ({
    default: ({ isOpen, feature }) =>
        isOpen ? <div data-testid="dialog" data-feature={feature} /> : null,
}))

import { UpgradePromptProvider } from './UpgradePromptProvider'
import { UpgradePromptContext } from './UpgradePromptContext'

function Trigger({ feature }) {
    const { triggerUpgradePrompt } = useContext(UpgradePromptContext)
    return <button onClick={() => triggerUpgradePrompt(feature)}>go</button>
}

describe('UpgradePromptProvider', () => {
    it('passes the named feature through to the dialog', () => {
        // Callers name the thing the user reached for — "Premium Export
        // Formats (STEP)" — and the provider used to discard it and hardcode
        // 'a Pro feature', making every upsell generic.
        render(
            <UpgradePromptProvider>
                <Trigger feature="Premium Export Formats (STEP)" />
            </UpgradePromptProvider>
        )
        fireEvent.click(screen.getByText('go'))
        expect(screen.getByTestId('dialog')).toHaveAttribute(
            'data-feature', 'Premium Export Formats (STEP)'
        )
    })

    it('falls back to a generic label when no feature is named', () => {
        render(
            <UpgradePromptProvider>
                <Trigger />
            </UpgradePromptProvider>
        )
        fireEvent.click(screen.getByText('go'))
        expect(screen.getByTestId('dialog')).toHaveAttribute('data-feature', 'a Pro feature')
    })
})
