'use client';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { LockIcon, CrownIcon as Crown } from 'hugeicons-react';
import Link from 'next/link';

interface UpsellModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  upgradeText?: string;
  onClose?: () => void;
}

export function UpsellModal({
  open,
  onOpenChange,
  title,
  description,
  upgradeText = 'Upgrade to Pro',
  onClose,
}: UpsellModalProps) {
  return (
    <>
      <style jsx>{`
        @keyframes shine {
          0% {
            left: -60%;
            opacity: 0.2;
          }
          20% {
            opacity: 0.6;
          }
          50% {
            left: 100%;
            opacity: 0.6;
          }
          80% {
            opacity: 0.2;
          }
          100% {
            left: 100%;
            opacity: 0;
          }
        }
        .animate-shine {
          position: absolute;
          top: 0;
          left: -60%;
          width: 60%;
          height: 100%;
          background: linear-gradient(90deg, transparent, #bfc4e0 60%, transparent);
          opacity: 0.7;
          border-radius: 0.375rem;
          animation: shine 2.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
          pointer-events: none;
        }
      `}</style>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
              <LockIcon className="h-6 w-6 text-gray-600 dark:text-gray-400" />
            </div>
            <DialogTitle className="text-center text-xl">{title}</DialogTitle>
            <DialogDescription className="text-center">{description}</DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex flex-row gap-2">
            <Button
              asChild
              size="default"
              className="relative h-10 w-1/2 items-center justify-center overflow-hidden border border-[#DEE0F4] bg-gradient-to-r from-[#DEE0F4] to-[#A3A8C9] font-medium text-[#141B34] hover:from-[#BFC4E0] hover:to-[#7B81A6] dark:border-[#A3A8C9] dark:text-[#23263A]"
            >
              <Link
                href="/settings/organization"
                className="relative z-0 flex h-full items-center justify-center gap-2"
              >
                <Crown className="h-5 w-5 text-current" />
                <span className="font-medium">{upgradeText}</span>
                <div className="animate-shine" />
              </Link>
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                onOpenChange(false);
                onClose?.();
              }}
              className="h-10 w-1/2 text-sm font-medium"
            >
              Maybe Later
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
