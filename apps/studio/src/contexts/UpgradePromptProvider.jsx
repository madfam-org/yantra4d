import React, { useState, useCallback } from 'react';
import UpgradeDialog from '../components/auth/UpgradeDialog';

import { UpgradePromptContext } from './UpgradePromptContext';

export function UpgradePromptProvider({ children }) {
    const [isOpen, setIsOpen] = useState(false);
    const [feature, setFeature] = useState('');

    const triggerUpgradePrompt = useCallback(() => {
        setFeature('a Pro feature');
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
