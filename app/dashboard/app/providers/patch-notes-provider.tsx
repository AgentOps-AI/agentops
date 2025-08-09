'use client';

import React, { createContext, useContext, useState } from 'react';
import { PatchNotesModal } from '@/components/patch-notes-modal';

interface PatchNotesContextType {
    openPatchNotes: () => void;
}

const PatchNotesContext = createContext<PatchNotesContextType | undefined>(undefined);

export const usePatchNotes = () => {
    const context = useContext(PatchNotesContext);
    if (!context) {
        throw new Error('usePatchNotes must be used within a PatchNotesProvider');
    }
    return context;
};

export function PatchNotesProvider({ children }: { children: React.ReactNode }) {
    const [isOpen, setIsOpen] = useState(false);

    const openPatchNotes = () => {
        setIsOpen(true);
    };

    return (
        <PatchNotesContext.Provider value={{ openPatchNotes }}>
            {children}
            <PatchNotesModal open={isOpen} onOpenChange={setIsOpen} />
        </PatchNotesContext.Provider>
    );
} 