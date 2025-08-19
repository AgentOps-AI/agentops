'use client';
import { ISpan } from '@/types/ISpan';
import { useState } from 'react';
import { SpanVisualizationList } from './span-visual-list';
import { Loader2 } from 'lucide-react';
import SpanAttributesViewer from '@/app/(with-layout)/traces/_components/span-attribute-viewer';

type ISpanWithChildren = ISpan & {
  children: ISpanWithChildren[];
};

type SpansListProps = {
  spans: ISpan[];
  loading: boolean;
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

// Process trace data to establish hierarchy
export const processTraceData = (spans: ISpan[]) => {
  // Create a map of span_id to span for quick lookup
  const spanMap: Record<string, ISpanWithChildren> = {};
  spans.forEach((span: ISpan) => {
    const spanWithChildren = span as ISpanWithChildren;
    spanWithChildren.children = [];
    spanMap[span.span_id] = spanWithChildren;
    spanWithChildren.durationMs = span.duration / 1000000;
  });

  // Build the hierarchy
  const rootSpans: ISpanWithChildren[] = [];
  spans.forEach((span: ISpan) => {
    const spanWithChildren = span as ISpanWithChildren;
    if (span.parent_span_id && spanMap[span.parent_span_id]) {
      const parentSpan = spanMap[span.parent_span_id];
      parentSpan.children.push(spanWithChildren);
    } else {
      rootSpans.push(spanWithChildren);
    }
  });

  return {
    rootSpans,
    allSpans: spans,
    spanMap,
  };
};

/**
 * Convert a flat list of spans into a hierarchical tree structure
 * @param {Array} spans - The flat list of spans
 * @return {Array} - The hierarchical tree structure
 */
export function buildSpansTree(spans: ISpan[]) {
  // Handle null/undefined spans
  if (!spans || !Array.isArray(spans) || spans.length === 0) {
    return [];
  }

  // Remove duplicates based on span_id
  const uniqueSpans = [];
  const seenIds = new Set();

  for (const span of spans) {
    if (span && span.span_id && !seenIds.has(span.span_id)) {
      uniqueSpans.push(span);
      seenIds.add(span.span_id);
    }
  }

  // Create a map of spans by id for easy lookup
  const spansMap: any = {};
  for (const span of uniqueSpans) {
    spansMap[span.span_id] = {
      ...span,
      children: [],
      originalSpan: span,
    };
  }

  // Collect all parent IDs
  const parentIds = new Set();
  const orphanedSpans = []; // Spans with non-existent parents
  const topLevelSpans = []; // Spans without parents

  for (const span of uniqueSpans) {
    if (span.parent_span_id) {
      parentIds.add(span.parent_span_id);
    } else {
      topLevelSpans.push(spansMap[span.span_id]);
    }
  }

  // Check which parent IDs exist in our spans
  const missingParentIds = new Set();
  for (const parentId of parentIds) {
    if (parentId && !spansMap[parentId as string]) {
      missingParentIds.add(parentId);
    }
  }

  // Build the tree structure
  for (const span of uniqueSpans) {
    const spanWithChildren = spansMap[span.span_id];

    // If this span has a parent and the parent exists in our map
    if (span.parent_span_id && spansMap[span.parent_span_id]) {
      // Add this span as a child of its parent
      spansMap[span.parent_span_id].children.push(spanWithChildren);
    }
    // If the span has a missing parent ID
    else if (span.parent_span_id && missingParentIds.has(span.parent_span_id)) {
      orphanedSpans.push(spanWithChildren);
    }
  }

  // If we have a common parent ID that's missing, we can create a virtual root
  if (missingParentIds.size === 1) {
    const missingParentId = Array.from(missingParentIds)[0];
    const commonParentSpans = orphanedSpans.filter(
      (span) => span.parent_span_id === missingParentId,
    );

    if (commonParentSpans.length > 0) {
      // Create a virtual root node for the common parent
      const virtualRoot = {
        span_id: missingParentId,
        span_name: 'Virtual Root',
        children: commonParentSpans,
        isVirtual: true,
        originalSpan: commonParentSpans[0],
      };

      return [...topLevelSpans, virtualRoot];
    }
  }

  // Combine top-level spans and orphaned spans if we don't have a common parent
  return [...topLevelSpans, ...orphanedSpans];
}
