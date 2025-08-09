'use client';
import React, { useState } from 'react';
import { ISpan } from '@/types/ISpan';
import { Badge } from '@/components/ui/badge';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { isRootSpan } from '@/utils/span.utils';

type SpanWithChildren = ISpan & {
  children?: SpanWithChildren[];
  durationMs?: number;
};

type SpanIconType = 'default' | 'tool' | 'agent' | 'request';

type SpanItemProps = {
  span: SpanWithChildren;
  depth?: number;
  maxDuration: number;
  hasChildren: boolean;
  isExpanded: boolean;
  onSpanClick: (span: SpanWithChildren) => void;
};

type SpanGroupProps = {
  span: SpanWithChildren;
  maxDuration: number;
  onSpanClick: (span: SpanWithChildren | null) => void;
};

type SpanVisualizationListProps = {
  spans: ISpan[];
  onSpanClick: (span: ISpan | null) => void;
};

const IconMap: Record<SpanIconType, JSX.Element> = {
  default: (
    <div className="mt-2 flex h-6 min-h-6 w-6 min-w-6 items-center justify-center rounded bg-gray-500 text-white">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
      </svg>
    </div>
  ),
  tool: (
    <div className="mt-2 flex h-6 min-h-6 w-6 min-w-6 items-center justify-center rounded bg-blue-500 text-white">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" id="code" fill="white">
        <path d="M9.651 8.241a1 1 0 00-1.41.109l-6 7a1 1 0 000 1.3l6 7a1 1 0 101.518-1.3L4.317 16 9.759 9.65A1 1 0 009.651 8.241zM29.759 15.35l-6-7a1 1 0 10-1.518 1.3L27.683 16l-5.442 6.35a1 1 0 101.518 1.3l6-7A1 1 0 0029.759 15.35zM19.394 8.081a1 1 0 00-1.313.525l-6 14a1 1 0 00.525 1.313A.979.979 0 0013 24a1 1 0 00.919-.606l6-14A1 1 0 0019.394 8.081z"></path>
      </svg>
    </div>
  ),
  agent: (
    <div className="mt-2 flex h-6 min-h-6 w-6 min-w-6 items-center justify-center rounded bg-green-500 text-white">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" id="cube" fill="white">
        <path d="M20.4896851,7.2872925c-0.0048828-0.0623169-0.0209351-0.1206665-0.0482178-0.177063c-0.0082397-0.0169678-0.0123291-0.0340576-0.0224609-0.0499878c-0.0391846-0.0621948-0.0886841-0.1184692-0.1553345-0.1598511l-8-4.9589844c-0.1616821-0.0996094-0.3656616-0.0996094-0.5273438,0l-8,4.9589844c-0.0136108,0.0084229-0.020813,0.0238647-0.0335083,0.0335083C3.6665649,6.9614258,3.6358643,6.9922485,3.6083374,7.0285034C3.5986328,7.0412598,3.5831909,7.0485229,3.574707,7.0621948c-0.006958,0.0112915-0.0072632,0.024231-0.0132446,0.0358276C3.5462036,7.1271973,3.5366821,7.1576538,3.5274048,7.1898193c-0.0094604,0.0332031-0.0176392,0.0651245-0.0200195,0.098938C3.5064087,7.3014526,3.5,7.3122559,3.5,7.3251953v9.3496094c-0.000061,0.1729736,0.0893555,0.3336182,0.2363281,0.4248047l8,4.9589844c0.0036011,0.0022583,0.0083618,0.0012817,0.0120239,0.003418c0.00354,0.0020752,0.0048828,0.0062866,0.0084839,0.0083008C11.8309937,22.1121826,11.9147949,22.1340332,12,22.1337891c0.0852051,0.0002441,0.1690063-0.0216064,0.2431641-0.0634766c0.0036011-0.0020142,0.0049438-0.0062256,0.0084839-0.0083008c0.0036621-0.0021362,0.0084229-0.0011597,0.0120239-0.003418l8-4.9589844c0.1468506-0.0913086,0.2362061-0.2518921,0.2363281-0.4248047V7.3251953C20.5,7.3116455,20.4907837,7.3006592,20.4896851,7.2872925z M11.5,20.7353516l-7-4.3388672V8.2236328l7,4.3378906V20.7353516z M12,11.6953125l-0.4055176-0.2513428L4.9492188,7.3251953L12,2.9541016l7.0507812,4.3710938l-5.1820679,3.211853L12,11.6953125z M19.5,16.3964844l-7,4.3388672v-8.1738281l7-4.3378906V16.3964844z"></path>
      </svg>
    </div>
  ),
  request: (
    <div className="mt-2 flex h-6 min-h-6 w-6 min-w-6 items-center justify-center rounded bg-blue-600 p-1 text-white">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" id="request" fill="white">
        <path d="M17.8,23.4c0.3,0.3,0.7,0.4,1.1,0.4s0.8-0.1,1.1-0.4c0.6-0.6,0.6-1.5,0-2.1l-4.1-4.1c-0.1-0.1-0.1-0.1-0.2-0.2c0,0,0,0-0.1,0c-0.1,0-0.1-0.1-0.2-0.1c0,0-0.1,0-0.1,0c-0.1,0-0.1,0-0.2-0.1c-0.1,0-0.2,0-0.3,0s-0.2,0-0.3,0c-0.1,0-0.1,0-0.2,0.1c0,0-0.1,0-0.1,0c-0.1,0-0.1,0.1-0.2,0.1c0,0,0,0-0.1,0c-0.1,0.1-0.2,0.1-0.2,0.2l-4.1,4.1c-0.6,0.6-0.6,1.5,0,2.1s1.5,0.6,2.1,0l1.6-1.6v14.9c0,2.7,2.2,5,5,5h10.2c0.8,0,1.5-0.7,1.5-1.5s-0.7-1.5-1.5-1.5H18.2c-1.1,0-2-0.9-2-2V21.9L17.8,23.4z" />
      </svg>
    </div>
  ),
};

const getSpanIcon = (span: SpanWithChildren): JSX.Element => {
  const spanType = (span.span_type as SpanIconType) || 'default';
  return IconMap[spanType];
};

const findMaxDuration = (spans: SpanWithChildren[]): number => {
  let max = 0;

  const checkSpan = (span: SpanWithChildren) => {
    if (span.duration > max) max = span.duration;
    if (span.children?.length) {
      span.children.forEach(checkSpan);
    }
  };

  spans.forEach(checkSpan);
  return max || 1; // Avoid division by zero
};

const SpanItem = ({
  span,
  depth = 0,
  maxDuration,
  hasChildren,
  isExpanded,
  onSpanClick,
}: SpanItemProps) => {
  const durationMs = (span.duration / 1000000).toFixed(0);
  const durationPercentage = (span.duration / maxDuration) * 100;
  const barPosition = 20;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'span-item flex items-center border-b border-black/10 py-2 transition-colors hover:bg-gray-900/5 dark:hover:bg-gray-100/5',
        hasChildren ? 'cursor-pointer' : '',
      )}
      onClick={() => {
        if (!hasChildren) {
          onSpanClick(span);
        }
      }}
      style={{ paddingRight: `15px` }}
    >
      <div className="flex items-start" style={{ paddingLeft: `${depth * 20}px` }}>
        {getSpanIcon(span)}
        {hasChildren && (
          <motion.div
            className="ml-2 flex items-center gap-2"
            initial={false}
            animate={{ rotate: isExpanded ? 90 : 0 }}
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </motion.div>
        )}
        <div className="ml-2 flex items-start gap-2">
          <div className="flex flex-col items-start">
            <span className="font-medium">{span.span_name}</span>
            {span.span_name && (
              <span
                className={cn(
                  'text-sm text-gray-500',
                  !span.service_name ? 'font-semibold text-black dark:text-white' : '',
                )}
              >
                {span.service_name}
              </span>
            )}
          </div>
          {span.span_kind && (
            <Badge variant="outline" className="text-xs">
              {span.span_kind}
            </Badge>
          )}
        </div>
      </div>
      <div className="ml-auto mr-2 font-mono text-xs">
        {!isNaN(+durationMs) ? durationMs : 0} ms
      </div>
      <div className="relative ml-2 h-2 w-40 overflow-hidden rounded-full bg-gray-800/20">
        <motion.div
          className="absolute h-full rounded-full bg-cyan-500/40"
          initial={{ width: 0 }}
          animate={{
            width: `${durationPercentage}%`,
            left: `${barPosition}%`,
            maxWidth: `${100 - barPosition}%`,
          }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
        <motion.div
          className="absolute h-full rounded-full bg-cyan-500"
          initial={{ width: 0 }}
          animate={{
            width: '4px',
            left: `${barPosition + durationPercentage / 4}%`,
          }}
          transition={{ duration: 0.5, delay: 0.2, ease: 'easeOut' }}
        />
      </div>
    </motion.div>
  );
};

const SpanGroup = ({ span, maxDuration, onSpanClick }: SpanGroupProps) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = Boolean(span.children?.length);

  const spanGroupClick = () => {
    if (hasChildren) {
      if (isRootSpan(span) && isExpanded) {
        setIsExpanded(false);
        onSpanClick(null);
      } else {
        setIsExpanded(!isExpanded);
        onSpanClick(span);
      }
    }
  };

  return (
    <div className="span-group">
      <div className="group" onClick={spanGroupClick}>
        <SpanItem
          hasChildren={hasChildren}
          isExpanded={isExpanded}
          span={span}
          maxDuration={maxDuration}
          onSpanClick={onSpanClick}
        />
      </div>

      <AnimatePresence>
        {isExpanded && hasChildren && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="children overflow-hidden"
          >
            {span.children?.map((child, idx) => (
              <div key={child.span_id + idx}>
                <SpanItem
                  hasChildren={Boolean(child.children?.length)}
                  isExpanded={false}
                  span={child}
                  depth={1}
                  maxDuration={maxDuration}
                  onSpanClick={onSpanClick}
                />
                {child.children?.map((grandchild, idx1) => (
                  <SpanItem
                    key={grandchild.span_id + idx1}
                    hasChildren={Boolean(grandchild.children?.length)}
                    isExpanded={false}
                    span={grandchild}
                    depth={2}
                    maxDuration={maxDuration}
                    onSpanClick={onSpanClick}
                  />
                ))}
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const processTraceData = (
  spans: ISpan[],
): {
  rootSpans: SpanWithChildren[];
  allSpans: ISpan[];
  spanMap: Record<string, SpanWithChildren>;
} => {
  const spanMap: Record<string, SpanWithChildren> = {};
  spans.forEach((span: ISpan) => {
    const spanWithChildren: SpanWithChildren = {
      ...span,
      children: [],
      durationMs: span.duration / 1000000,
    };
    spanMap[span.span_id] = spanWithChildren;
  });

  const rootSpans: SpanWithChildren[] = [];
  spans.forEach((span: ISpan) => {
    if (span.parent_span_id && spanMap[span.parent_span_id]) {
      spanMap[span.parent_span_id].children?.push(spanMap[span.span_id]);
    } else {
      rootSpans.push(spanMap[span.span_id]);
    }
  });

  return { rootSpans, allSpans: spans, spanMap };
};

const buildSpansTree = (spans: ISpan[]): SpanWithChildren[] => {
  const uniqueSpans: SpanWithChildren[] = [];
  const seenIds = new Set<string>();

  for (const span of spans) {
    if (!seenIds.has(span.span_id)) {
      uniqueSpans.push({
        ...span,
        children: [],
        durationMs: span.duration / 1000000,
      });
      seenIds.add(span.span_id);
    }
  }

  const spansMap: Record<string, SpanWithChildren> = {};
  for (const span of uniqueSpans) {
    spansMap[span.span_id] = {
      ...span,
      children: [],
    };
  }

  const parentIds = new Set<string>();
  const orphanedSpans: SpanWithChildren[] = [];
  const topLevelSpans: SpanWithChildren[] = [];

  for (const span of uniqueSpans) {
    if (span.parent_span_id) {
      parentIds.add(span.parent_span_id);
    } else {
      topLevelSpans.push(spansMap[span.span_id]);
    }
  }

  const missingParentIds = new Set<string>();
  for (const parentId of parentIds) {
    if (parentId && !spansMap[parentId]) {
      missingParentIds.add(parentId);
    }
  }

  for (const span of uniqueSpans) {
    const spanWithChildren = spansMap[span.span_id];

    if (span.parent_span_id && spansMap[span.parent_span_id]) {
      spansMap[span.parent_span_id].children?.push(spanWithChildren);
    } else if (span.parent_span_id && missingParentIds.has(span.parent_span_id)) {
      orphanedSpans.push(spanWithChildren);
    }
  }

  if (missingParentIds.size === 1) {
    const missingParentId = Array.from(missingParentIds)[0];
    const commonParentSpans = orphanedSpans.filter(
      (span) => span.parent_span_id === missingParentId,
    );

    if (commonParentSpans.length > 0) {
      const virtualRoot: SpanWithChildren = {
        span_id: missingParentId,
        parent_span_id: '',
        span_name: 'Virtual Root',
        span_kind: '',
        service_name: '',
        start_time: '0',
        end_time: '0',
        duration: 0,
        durationMs: 0,
        status_code: '',
        status_message: '',
        attributes: {},
        resource_attributes: {},
        event_timestamps: [],
        event_names: [],
        event_attributes: [],
        link_trace_ids: [],
        link_span_ids: [],
        link_trace_states: [],
        link_attributes: [],
        span_type: '',
        span_attributes: {},
        children: commonParentSpans,
      };

      return [...topLevelSpans, virtualRoot];
    }
  }

  return [...topLevelSpans, ...orphanedSpans];
};

export const SpanVisualizationList = ({ spans, onSpanClick }: SpanVisualizationListProps) => {
  const organizedSpans = buildSpansTree(spans || []);
  const hierarchicalSpans = processTraceData(spans);
  const maxDuration = findMaxDuration(organizedSpans);

  const handleSpanClick = (span: SpanWithChildren | null) => {
    onSpanClick(span);
  };

  return (
    <div className="trace-visualization w-full text-sm">
      <AnimatePresence>
        {hierarchicalSpans.rootSpans.map((span, idx) => (
          <SpanGroup
            key={span.span_id + idx}
            span={span}
            maxDuration={maxDuration}
            onSpanClick={handleSpanClick}
          />
        ))}
      </AnimatePresence>
    </div>
  );
};
