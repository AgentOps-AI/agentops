'use client';

import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from '@/components/ui/toast';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';
import { BackgroundImageOverlay } from './background-image-overlay';

export function Toaster() {
  const { toasts } = useToast();

  return (
    <ToastProvider>
      {toasts.map(function ({ id, title, description, action, icon, ...props }) {
        return (
          <Toast
            key={id}
            {...props}
            data-testid={`toast-${props.variant || 'default'}-${id.replace(/[^a-zA-Z0-9-_]/g, '')}`}
            className="relative rounded-lg border border-white bg-[#F7F8FF] px-2 py-4"
          >
            <BackgroundImageOverlay />
            <div className="grid gap-1">
              <div className="flex items-center gap-2">
                {icon && <div>{icon}</div>}
                {title && (
                  <ToastTitle className="font-medium text-secondary dark:text-white">
                    {title}
                  </ToastTitle>
                )}
              </div>
              {description && (
                <ToastDescription
                  className={cn('font-medium text-primary', icon ? 'pl-8' : 'pl-0')}
                >
                  {description}
                </ToastDescription>
              )}
            </div>
            {action}
            <ToastClose />
          </Toast>
        );
      })}
      <ToastViewport />
    </ToastProvider>
  );
}
