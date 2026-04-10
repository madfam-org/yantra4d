import { createContext } from 'react';

export interface UpgradePromptContextValue {
    triggerUpgradePrompt: (feature?: string) => void
    closeUpgradePrompt: () => void
}

export const UpgradePromptContext = createContext<UpgradePromptContextValue>({
    triggerUpgradePrompt: () => { },
    closeUpgradePrompt: () => { },
});
