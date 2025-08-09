import React from 'react';
import { ReadOnlyCodeViewer } from '@/components/ui/read-only-code-viewer';
import { ISpan } from '@/types/ISpan';

type LlmSpanRawProps = {
  selectedSpan: ISpan | null;
  isFullWidth?: boolean;
};

export const LlmSpanRaw = ({ selectedSpan, isFullWidth = false }: LlmSpanRawProps) => {
  if (!selectedSpan) {
    return (
      <div
        className={`flex h-full min-h-0 items-center justify-center rounded-md border border-dashed text-gray-500 dark:border-slate-700 ${isFullWidth ? 'col-span-5' : 'col-span-2'}`}
      >
        Select a span in the chart to view raw details.
      </div>
    );
  }

  const stringifiedSpan = JSON.stringify(selectedSpan, null, 2);

  return (
    <div data-testid="trace-detail-span-raw-content" className="h-full w-full">
      <ReadOnlyCodeViewer
        language="json"
        value={stringifiedSpan}
        height="65vh"
        title="raw span data"
        className="w-full"
      />
    </div>
  );
};
