'use client';
import { ISpan } from '@/types/ISpan';
import { useState } from 'react';
import { SpanVisualizationList } from './span-visual-list';
import { Loader2 } from 'lucide-react';
import SpanAttributesViewer from './span-attribute-viewer';

type SpansListProps = {
  spans: ISpan[];
  loading: boolean;
  traceId: string;
};

export const SpansList = ({ spans, loading }: SpansListProps) => {
  const [selectedSpan, setSelectedSpan] = useState<ISpan | null>(null);

  const onSpanClick = (span: ISpan | null) => {
    setSelectedSpan(span);
  };

  return (
    <div className="grid w-full grid-cols-3 gap-2">
      <div className="sticky top-0 col-span-1">
        <SpanVisualizationList spans={spans} onSpanClick={onSpanClick} />
      </div>
      <div className="col-span-2">
        {!selectedSpan ? (
          <div className="text-sm text-muted-foreground">
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              'Select a span to view details'
            )}
          </div>
        ) : (
          <div className="hide-scrollbar sticky top-[54px] h-[calc(100vh-78px)] overflow-y-auto overflow-x-hidden">
            <SpanAttributesViewer showHeader={false} span={selectedSpan} />
          </div>
        )}
      </div>
    </div>
  );
};
