import { useContext } from 'react';
import { UpgradePromptContext } from '../../contexts/auth/UpgradePromptContext';

interface UpgradePromptHook {
  triggerUpgradePrompt: (feature?: string) => void
  closeUpgradePrompt: () => void
}

export const useUpgradePrompt = (): UpgradePromptHook => useContext(UpgradePromptContext);
