import { createContext } from 'react';

export interface UpgradePromptOptions {
    /** What the visitor can do for free instead, one sentence each, shown under the offer. */
    alternatives?: string[]
}

export interface UpgradePromptContextValue {
    triggerUpgradePrompt: (feature?: string, options?: UpgradePromptOptions) => void
    closeUpgradePrompt: () => void
}

export const UpgradePromptContext = createContext<UpgradePromptContextValue>({
    triggerUpgradePrompt: () => { },
    closeUpgradePrompt: () => { },
});
