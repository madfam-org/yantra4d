import { useContext } from 'react';
import { UpgradePromptContext } from '../../contexts/auth/UpgradePromptContext';

export const useUpgradePrompt = () => useContext(UpgradePromptContext);
