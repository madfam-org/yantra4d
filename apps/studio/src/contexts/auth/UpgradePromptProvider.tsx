import React, { useState, useCallback } from 'react';
import UpgradeDialog from '../../components/auth/UpgradeDialog';

import { UpgradePromptContext } from './UpgradePromptContext';

interface UpgradePromptProviderProps {
    children: React.ReactNode
}

export function UpgradePromptProvider({ children }: UpgradePromptProviderProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [feature, setFeature] = useState('');

    const triggerUpgradePrompt = useCallback((feature?: string) => {
        // Callers pass the specific thing the user just reached for —
        // "Premium Export Formats (STEP)", "CadQuery Cloud Rendering" — and
        // this used to discard it and hardcode 'a Pro feature', so every
        // upsell was generic. Show what they actually wanted.
        setFeature(feature || 'a Pro feature');
        setIsOpen(true);
    }, []);

    const closeUpgradePrompt = useCallback(() => {
        setIsOpen(false);
        setTimeout(() => setFeature(''), 300); // Clear after animation
    }, []);

    return (
        <UpgradePromptContext.Provider value={{ triggerUpgradePrompt, closeUpgradePrompt }}>
            {children}
            <UpgradeDialog isOpen={isOpen} onClose={closeUpgradePrompt} feature={feature} />
        </UpgradePromptContext.Provider>
    );
}
