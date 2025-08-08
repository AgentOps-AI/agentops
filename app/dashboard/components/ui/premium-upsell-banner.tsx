'use client';

import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { ReactNode } from 'react';
import { InformationCircleIcon as Info } from 'hugeicons-react';

interface UpsellBannerProps {
  title: string;
  messages: string[];
  ctaText?: string;
  ctaHref?: string;
  icon?: ReactNode;
}

export function PremiumUpsellBanner({
  title,
  messages,
  ctaText = 'Upgrade to Pro',
  ctaHref = '/settings/organization',
  icon: _icon,
}: UpsellBannerProps) {
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
      <div className="mb-4 inline-flex w-auto rounded-lg border border-[#DEE0F4] bg-gradient-to-r from-[#F5F7FB] to-[#E1E3F2] p-2 shadow-sm dark:border-[#A3A8C9] dark:from-[#23263A]/20 dark:to-[#3A3E5A]/20">
        <div className="flex w-auto flex-col items-start gap-1 sm:flex-row sm:items-center">
          <div className="flex w-auto flex-row items-start gap-1">
            <Info className="mr-2 mt-0.5 h-4 w-4 flex-shrink-0 text-[#141B34] dark:text-[#E1E2F2]" />
            <div className="flex w-full flex-col gap-0.5">
              <h3 className="text-sm font-semibold leading-tight text-[#141B34] dark:text-[#E1E2F2] sm:text-base">
                {title}
              </h3>
              <div className="space-y-0.5 text-left">
                {messages.map((message, index) => (
                  <p
                    key={index}
                    className="text-left text-xs leading-snug text-[#28304B] dark:text-[#A3A8C9] sm:text-sm"
                  >
                    {messages.length > 1 ? `• ${message}` : message}
                  </p>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-1 flex-shrink-0 sm:ml-2 sm:mt-0">
            <Button
              asChild
              size="lg"
              className="relative mt-0 inline-flex h-8 w-auto items-center overflow-hidden border border-[#DEE0F4] bg-gradient-to-r from-[#DEE0F4] to-[#A3A8C9] px-3 py-1 text-xs text-[#141B34] hover:from-[#BFC4E0] hover:to-[#7B81A6] dark:border-[#A3A8C9] dark:text-[#23263A]"
            >
              <Link href={ctaHref} className="relative z-0 flex h-full items-center">
                <span className="font-semibold">{ctaText}</span>
                <div className="animate-shine" />
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
