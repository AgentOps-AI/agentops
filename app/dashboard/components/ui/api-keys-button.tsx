'use client';

import { Key01Icon } from 'hugeicons-react';
import { cn } from '@/lib/utils';
import React, { useState } from 'react';
import { buttonVariants } from './button';
import { ApiKeysModal } from './api-keys-modal';

export const ApiKeysButton = ({
    withTitle,
    alignLeft,
}: {
    withTitle?: boolean;
    alignLeft?: boolean;
}) => {
    const [modalOpen, setModalOpen] = useState(false);

    return (
        <>
            <div
                className={cn(
                    buttonVariants({
                        variant: 'ghost',
                        size: 'sm',
                    }),
                    'justify-start overflow-hidden rounded-lg border-4 border-transparent px-1.5 dark:border-none dark:px-2.5',
                    'flex cursor-pointer items-center hover:bg-[#E4E6F4] dark:hover:bg-slate-800',
                    alignLeft ? 'justify-start' : withTitle ? 'justify-start' : 'justify-center',
                    withTitle && 'w-full',
                    'dark:text-white',
                )}
                onClick={() => setModalOpen(true)}
            >
                <div className="flex items-center">
                    <Key01Icon className="h-4 w-4" />
                    {withTitle && (
                        <span className="ml-3 whitespace-nowrap dark:text-white">API Keys</span>
                    )}
                </div>
            </div>

            <ApiKeysModal open={modalOpen} onOpenChange={setModalOpen} />
        </>
    );
}; 