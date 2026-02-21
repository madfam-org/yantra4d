import { useContext } from 'react';
import { UpgradePromptContext } from '../contexts/UpgradePromptContext';

export const useUpgradePrompt = () => useContext(UpgradePromptContext);
