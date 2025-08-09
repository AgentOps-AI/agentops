'use client';
import React, { useState } from 'react';
import { ISpan } from '@/types/ISpan';
import { buildSpansTree, processTraceData } from './spans-list';
import { Badge } from './ui/badge';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { isRootSpan } from '@/utils/span.utils';

// Function to find maximum duration for scaling
const findMaxDuration = (spans: ISpan[]) => {
  let max = 0;

  const checkSpan = (span: any) => {
    if (span.duration > max) max = span.duration;
    if (span.children && span.children.length > 0) {
      span.children.forEach(checkSpan);
    }
  };

  spans.forEach(checkSpan);
  return max || 1; // Avoid division by zero
};

// Icons for different span types
const IconMap = {
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
        <path
          d="M17.8,23.4c0.3,0.3,0.7,0.4,1.1,0.4s0.8-0.1,1.1-0.4c0.6-0.6,0.6-1.5,0-2.1l-4.1-4.1c-0.1-0.1-0.1-0.1-0.2-0.2
        c0,0,0,0-0.1,0c-0.1,0-0.1-0.1-0.2-0.1c0,0-0.1,0-0.1,0c-0.1,0-0.1,0-0.2-0.1c-0.1,0-0.2,0-0.3,0s-0.2,0-0.3,0c-0.1,0-0.1,0-0.2,0.1
        c0,0-0.1,0-0.1,0c-0.1,0-0.1,0.1-0.2,0.1c0,0,0,0-0.1,0c-0.1,0.1-0.2,0.1-0.2,0.2l-4.1,4.1c-0.6,0.6-0.6,1.5,0,2.1s1.5,0.6,2.1,0
        l1.6-1.6v14.9c0,2.7,2.2,5,5,5h10.2c0.8,0,1.5-0.7,1.5-1.5s-0.7-1.5-1.5-1.5H18.2c-1.1,0-2-0.9-2-2V21.9L17.8,23.4z"
        ></path>
        <path d="M37.6 9.7c-.8 0-1.7.1-2.5.3C34.3 4.6 29.6.5 24 .5c-5.6 0-10.3 4.1-11.1 9.5-.8-.2-1.7-.3-2.5-.3-5.5 0-9.9 4.4-9.9 9.8 0 4.4 3 8.3 7.4 9.5.8.2 1.6-.3 1.8-1.1S9.4 26.2 8.6 26c-3-.8-5.1-3.5-5.1-6.5 0-3.7 3.1-6.8 6.9-6.8 1.1 0 2.2.3 3.2.8.5.2 1.1.2 1.5-.1.5-.3.7-.8.7-1.3l0-.2c0-.1 0-.2 0-.3 0-4.5 3.7-8.1 8.2-8.1s8.2 3.6 8.2 8.1c0 .1 0 .2 0 .3l0 .2c0 .5.2 1.1.7 1.3.5.3 1 .3 1.5.1 1-.5 2.1-.8 3.2-.8 3.8 0 6.9 3 6.9 6.8s-3.1 6.8-6.9 6.8H20.3c-.8 0-1.5.7-1.5 1.5s.7 1.5 1.5 1.5h17.3c5.5 0 9.9-4.4 9.9-9.8S43.1 9.7 37.6 9.7zM40.2 32.9c-4 0-7.3 3.3-7.3 7.3s3.3 7.3 7.3 7.3 7.3-3.3 7.3-7.3S44.2 32.9 40.2 32.9zM40.2 44.5c-2.4 0-4.3-1.9-4.3-4.3s1.9-4.3 4.3-4.3 4.3 1.9 4.3 4.3S42.6 44.5 40.2 44.5z"></path>
        <path d="M40.2,38.5c-0.9,0-1.7,0.7-1.7,1.7c0,0.9,0.7,1.7,1.7,1.7c0.9,0,1.7-0.7,1.7-1.7C41.8,39.3,41.1,38.5,40.2,38.5z"></path>
      </svg>
    </div>
  ),
};

// Get span type icon based on span name or kind
const getSpanIcon = (span: any) => {
  if (span.span_type === 'agent') {
    return IconMap.agent;
  } else if (span.span_type === 'tool') {
    return IconMap.tool;
  } else if (span.span_type === 'request') {
    return IconMap.request;
  } else {
    return IconMap.default;
  }
};

// Component for a single span
const SpanItem = ({ span, depth = 0, maxDuration, hasChildren, isExpanded, onSpanClick }: any) => {
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

// Component for a group of spans (a span and its children)
const SpanGroup = ({ span, maxDuration, onSpanClick }: any) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = span.children && span.children.length > 0;

  const spanGroupClick = () => {
    if (hasChildren) {
      // If the span is the root span and it's expanded,
      // collapse it and set the selected span to null
      if (isRootSpan(span) && isExpanded) {
        setIsExpanded(false);
        onSpanClick(null);
      } else {
        // Otherwise, toggle the expansion state and set
        // the selected span to the current span
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
            {span.children.map((child: any, idx: number) => (
              <div key={child.span_id + idx}>
                <SpanItem
                  span={child}
                  depth={1}
                  maxDuration={maxDuration}
                  onSpanClick={onSpanClick}
                />
                {child.children &&
                  child.children.map((grandchild: any, idx1: number) => (
                    <SpanItem
                      key={grandchild.span_id + idx1}
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

type SpanVisualizationListProps = {
  spans: ISpan[];
  onSpanClick: (span: ISpan) => void;
};

export const SpanVisualizationList = ({ spans, onSpanClick }: SpanVisualizationListProps) => {
  const organizedSpans = buildSpansTree(spans || []);
  const hierarchicalSpans = processTraceData(spans);
  const maxDuration = findMaxDuration(organizedSpans);

  return (
    <div className="trace-visualization w-full text-sm">
      <AnimatePresence>
        {hierarchicalSpans.rootSpans.map((span: any, idx: number) => (
          <SpanGroup
            key={span.span_id + idx}
            span={span}
            maxDuration={maxDuration}
            onSpanClick={onSpanClick}
          />
        ))}
      </AnimatePresence>
    </div>
  );
};
