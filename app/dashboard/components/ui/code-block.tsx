'use client';
import { Card } from '@/components/ui/card';
import { Container } from '@/components/ui/container';
import { toast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';
import { ReactNode } from 'react';
import { CopyButton } from './copy-button';

interface CodeBlockProps {
  dataToCopy?: string;
  title?: string;
  children?: ReactNode;
  styles?: string;
  scroll?: boolean;
  forceDarkMode?: boolean;
  copyButtonPlacement?: 'top' | 'overlay';
}

export const CodeBlock = ({
  dataToCopy,
  title,
  children,
  styles,
  forceDarkMode = false,
  copyButtonPlacement = 'top',
}: CodeBlockProps) => {
  const handleCopy = () => {
    if (!dataToCopy) return;
    navigator.clipboard.writeText(dataToCopy);
    toast({
      title: 'Copied to clipboard',
      description: `${title || 'Content'} has been copied.`,
    });
  };

  return (
    <Card
      className="flex h-full flex-col items-stretch rounded-lg border border-none overflow-hidden"
    >
      <>
        {(title || copyButtonPlacement === 'top') && (
          <div
            className="flex w-full flex-shrink-0 items-center justify-between rounded-t-lg border-b border-[#DEE0F4]/30 bg-[hsl(222.2_44%_14%)] px-2 py-0.5"
          >
            <h4
              className="pl-2 text-sm font-medium text-white"
            >
              {title}
            </h4>
            {copyButtonPlacement === 'top' && (
              <CopyButton
                title="Copy"
                iconClassName="ml-2 h-[18px] w-[18px] stroke-white"
                className="px-3"
                onClick={handleCopy}
                disabled={!dataToCopy}
              />
            )}
          </div>
        )}
      </>
      <div className="relative flex-1 min-h-0 rounded-b-lg bg-[hsl(222.2_44%_14%)]">
        <div
          className={cn(
            'absolute inset-0 overflow-auto px-4 pb-4 pt-5 text-xs text-white',
            '[&::-webkit-scrollbar]:h-1.5 [&::-webkit-scrollbar]:w-1.5',
            '[&::-webkit-scrollbar-track]:bg-transparent',
            '[&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-400/50',
            '[&::-webkit-scrollbar-thumb:hover]:bg-gray-500/70',
            '[scrollbar-width:thin]',
            '[scrollbar-color:rgba(156,163,175,0.5)_transparent]',
            styles,
          )}
          style={{
            fontFamily: 'Menlo',
          }}
        >
          {children || <pre>{dataToCopy}</pre>}
        </div>
        {copyButtonPlacement === 'overlay' && (
          <CopyButton
            title="Copy"
            className="absolute right-10 top-2 z-10 rounded p-1 text-xs bg-gray-600/50 text-white hover:bg-gray-700/70"
            iconClassName="h-[14px] w-[24px] stroke-white"
            onClick={handleCopy}
            disabled={!dataToCopy}
          />
        )}
      </div>
    </Card>
  );
};
