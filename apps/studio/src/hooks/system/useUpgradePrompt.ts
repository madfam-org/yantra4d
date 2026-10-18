import { useContext } from 'react';
import { UpgradePromptContext, type UpgradePromptOptions } from '../../contexts/auth/UpgradePromptContext';

interface UpgradePromptHook {
  triggerUpgradePrompt: (feature?: string, options?: UpgradePromptOptions) => void
  closeUpgradePrompt: () => void
}

export const useUpgradePrompt = (): UpgradePromptHook => useContext(UpgradePromptContext);
