import { createContext } from 'react';

export const UpgradePromptContext = createContext({
    triggerUpgradePrompt: () => { },
    closeUpgradePrompt: () => { },
});
