import React from 'react';
import MonacoEditor from '@monaco-editor/react';
import { Copy } from 'lucide-react';
import { toast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';

interface ReadOnlyCodeViewerProps {
  language: string;
  value: string;
  height?: string;
  className?: string;
  title?: string;
}

export const ReadOnlyCodeViewer: React.FC<ReadOnlyCodeViewerProps> = ({
  language,
  value,
  height = '200px',
  className,
  title = 'code snippet',
}) => {
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      toast({
        title: 'Copied to Clipboard',
      });
    } catch (error) {
      toast({
        title: '❌ Could Not Access Clipboard',
        description: 'Please ensure clipboard permissions are granted.',
        variant: 'destructive',
      });
      console.error('Failed to copy:', error);
    }
  };

  return (
    <div
      className={cn('relative w-full overflow-hidden rounded-md bg-gray-900', className)}
      style={{ height: height }}
    >
      <MonacoEditor
        language={language}
        theme="vs-dark"
        options={{
          tabSize: 2,
          insertSpaces: true,
          readOnly: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          padding: { top: 10, bottom: 10 },
          automaticLayout: true,
        }}
        value={value}
      />
      <button
        onClick={handleCopy}
        className="absolute right-2 top-2 z-10 rounded-md bg-gray-700 p-1.5 text-gray-300 transition-colors duration-150 hover:bg-gray-600"
        aria-label={`Copy ${title}`}
      >
        <Copy size={16} />
      </button>
    </div>
  );
};
