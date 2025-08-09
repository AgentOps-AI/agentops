import { ReactNode, useEffect, useState, useCallback, useRef } from 'react';
import { DismissableLayer } from '@radix-ui/react-dismissable-layer';
import { toast } from '@/components/ui/use-toast';
import { CopyButton } from '@/components/ui/copy-button';
import {
  ArrowLeft01Icon,
  ArrowExpandIcon,
  RefreshIcon as RefreshCcwIcon,
  Download01Icon as DownloadIcon,
} from 'hugeicons-react';
import { CommonTooltip } from '@/components/ui/common-tooltip';
import { cn, formatDate } from '@/lib/utils';
import { ISpan } from '@/types/ISpan';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Copy, FileDown } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { BookmarkButton } from '@/components/ui/bookmark-button';

interface BaseDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClose?: () => void;
  id: string;
  title?: string;
  isRefreshing?: boolean;
  onRefresh?: () => void;
  onExpand?: () => void;
  onExport?: () => void;
  onCopyJson?: () => void;
  headerContent?: ReactNode;
  stickyContent?: ReactNode;
  children: ReactNode;
  firstSpan?: ISpan;
  isBookmarked?: boolean;
  onToggleBookmark?: () => void;
}

const onCopyClick = (id: string | undefined) => {
  if (!id) return;
  navigator.clipboard
    .writeText(id)
    .then(() =>
      toast({
        title: 'ID Copied to Clipboard',
        description: id,
      }),
    )
    .catch(() => {
      toast({
        title: '❌ Could Not Access Clipboard - Manually copy the ID below:',
        description: id,
      });
    });
};

// Format span name helper function (duplicated from traces page)
const formatSpanName = (name: string): string => {
  if (name.endsWith('.session')) {
    const prefix = name.slice(0, name.lastIndexOf('.session'));
    return prefix
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join('_');
  }

  if (name.startsWith('llm:')) {
    return name.slice(4);
  }

  let formattedName = name
    .replace(/\./g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');

  formattedName = formattedName.replace(/Openai/g, 'OpenAI').replace(/Crewai/g, 'CrewAI');

  return formattedName;
};

/**
 * BaseDrilldownDrawer is a component that provides a base layout for drilldown drawers.
 * It includes a header with a title, ID, and optional content, a sticky content section,
 * and a main content section that fills the remaining space and scrolls if needed.
 *
 * There are more props, but the primary ones for layout are:
 * @param {Object} props - The component props
 * @param {string} props.title - The title of the drawer
 * @param {ReactNode} props.headerContent - Content to render within the header section
 * @param {ReactNode} props.stickyContent - Content to render in a sticky section below the header
 * @param {ReactNode} props.children - Main content of the drawer, fills remaining space and scrolls if needed
 *
 * The header is always there at the top, the sticky content is like a configurable sub-header,
 * and the children is the main content of the drawer.
 */

export const BaseDrilldownDrawer = ({
  open,
  onOpenChange,
  onClose,
  id,
  title = 'Trace ID',
  isRefreshing = false,
  onRefresh,
  onExpand,
  onExport,
  onCopyJson,
  headerContent,
  stickyContent,
  children,
  firstSpan,
  isBookmarked = false,
  onToggleBookmark,
}: BaseDrawerProps) => {
  const [localRefreshing, setLocalRefreshing] = useState(false);
  const [drawerWidth, setDrawerWidth] = useState(85); // Width as percentage
  const [isDragging, setIsDragging] = useState(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(85);

  // Lock body scroll when drawer is open
  useEffect(() => {
    if (open) {
      // Save current body overflow style
      const originalOverflow = document.body.style.overflow;
      const originalPaddingRight = document.body.style.paddingRight;

      // Check if scrollbar is present
      const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;

      // Lock body scroll and add padding to prevent layout shift
      document.body.style.overflow = 'hidden';
      if (scrollbarWidth > 0) {
        document.body.style.paddingRight = `${scrollbarWidth}px`;
      }

      // Cleanup function to restore original styles
      return () => {
        document.body.style.overflow = originalOverflow;
        document.body.style.paddingRight = originalPaddingRight;
      };
    }
  }, [open]);

  // Handle mouse events for dragging
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = dragStartX.current - e.clientX;
      const windowWidth = window.innerWidth;
      const newWidthPercent = Math.max(30, Math.min(95, dragStartWidth.current + (deltaX / windowWidth) * 100));
      setDrawerWidth(newWidthPercent);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  const handleDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartX.current = e.clientX;
    dragStartWidth.current = drawerWidth;
  };

  const handleBackClick = useCallback(() => {
    onOpenChange(false);
    onClose?.();
  }, [onOpenChange, onClose]);

  const handleRefresh = async () => {
    if (localRefreshing || !onRefresh) return;

    setLocalRefreshing(true);

    // Call the refresh function
    onRefresh();

    // Ensure minimum spin duration (at least 2 full rotations - 1 second)
    setTimeout(() => {
      setLocalRefreshing(false);
      toast({
        title: 'Data refreshed',
        description: 'Successfully fetched the latest data',
      });
    }, 1000);
  };

  if (!open) return null;

  return (
    <DismissableLayer
      onDismiss={handleBackClick}
      onPointerDownOutside={(event) => {
        const target = event.target as HTMLElement;
        if (
          target.closest('[data-radix-toast-primitive-root]') ||
          target.closest('[data-radix-toast-primitive-viewport]')
        ) {
          event.preventDefault();
        }
      }}
    >
      <div
        id="main-drawer"
        data-testid="trace-detail-drawer"
        className="fixed right-0 top-0 flex h-screen flex-col overflow-hidden rounded-l-2xl bg-[#F7F8FF] shadow-xl dark:border dark:border-white/50 dark:bg-slate-900 max-sm:w-full"
        style={{ 
          zIndex: 50,
          width: `${drawerWidth}%`,
          cursor: isDragging ? 'col-resize' : 'default'
        }}
      >
        {/* Drag handle */}
        <div
          className="absolute left-0 top-0 h-full w-2 cursor-col-resize bg-transparent hover:bg-blue-500/10 transition-colors duration-200 z-20"
          onMouseDown={handleDragStart}
          style={{ cursor: 'col-resize' }}
        >
          <div className="absolute left-0 top-1/2 transform -translate-y-1/2 w-1 h-12 bg-blue-500/30 rounded-r-sm opacity-0 hover:opacity-100 transition-opacity duration-200 flex items-center justify-center">
            <div className="w-0.5 h-6 bg-blue-500/60 rounded-full" />
          </div>
        </div>

        <div
          data-testid="trace-detail-header"
          className="sticky top-0 z-10 border-b border-gray-200 bg-[#F7F8FF] pb-2 pl-4 pr-4 pt-4 dark:border-gray-700 dark:bg-slate-900"
        >
          <div className="flex items-center gap-2">
            <ArrowLeft01Icon className="h-6 w-6 cursor-pointer" onClick={handleBackClick} />
            <div className={'flex flex-col gap-0.5'}>
              {!firstSpan ? (
                <>
                  <Skeleton className="h-6 w-48" />
                  <Skeleton className="h-4 w-64" />
                </>
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <CommonTooltip
                      content={
                        firstSpan.span_name.endsWith('.session')
                          ? firstSpan.span_name.slice(0, firstSpan.span_name.lastIndexOf('.session'))
                          : firstSpan.span_name
                      }
                      toolTipContentProps={{ sideOffset: 8 }}
                    >
                      <div className="max-w-md truncate text-lg font-semibold max-sm:max-w-xs max-sm:text-base">
                        {firstSpan.span_name.endsWith('.session')
                          ? firstSpan.span_name.slice(0, firstSpan.span_name.lastIndexOf('.session'))
                          : firstSpan.span_name}
                      </div>
                    </CommonTooltip>
                    {/* Show warning icon for unnamed traces */}
                    {formatSpanName(firstSpan.span_name) === 'Default' && (
                      <TooltipProvider>
                        <Tooltip delayDuration={0}>
                          <TooltipTrigger asChild>
                            <div
                              className="h-4 w-4 flex-shrink-0 flex items-center justify-center border border-yellow-500 text-yellow-500 rounded-full text-xs font-bold cursor-help"
                              aria-label="Unnamed trace information"
                            >
                              ?
                            </div>
                          </TooltipTrigger>
                          <TooltipContent
                            className="w-1/5 rounded-xl bg-primary/80 p-3 font-light text-[#EBECF8] backdrop-blur-md sm:ml-64 sm:w-80"
                            side="bottom"
                            sideOffset={8}
                          >
                            <div className="space-y-2">
                              <p className="font-medium">This trace is unnamed</p>
                              <p>
                                You can name your traces when creating them manually. This helps organize and identify your traces more easily.
                              </p>
                              <a
                                href="https://docs.agentops.ai/v2/concepts/traces#manual-trace-creation"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-block text-blue-300 hover:text-blue-200 underline"
                              >
                                Learn how to create named traces →
                              </a>
                            </div>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    )}
                  </div>
                  <div className="flex items-center gap-1 text-xs font-normal text-gray-500 dark:text-gray-400">
                    {id || 'No ID Selected'}
                    <CopyButton
                      withTooltip={'Copy ID'}
                      className="h-3 w-3 cursor-pointer"
                      onClick={() => onCopyClick(id)}
                    />
                    {firstSpan?.start_time && (
                      <>
                        <span className="mx-1">•</span>
                        <span>{formatDate(firstSpan.start_time)}</span>
                      </>
                    )}
                  </div>
                </>
              )}
              {headerContent && <>{headerContent}</>}
            </div>

            <div className="ml-auto flex items-center gap-2">
              {onToggleBookmark && (
                <BookmarkButton
                  isBookmarked={isBookmarked}
                  onClick={onToggleBookmark}
                  size="md"
                />
              )}
              {onRefresh && (
                <CommonTooltip content="Refresh" toolTipContentProps={{ sideOffset: 8 }}>
                  <RefreshCcwIcon
                    className={cn(
                      'h-4 w-4 cursor-pointer transition-opacity',
                      (localRefreshing || isRefreshing) &&
                        'animate-spin cursor-not-allowed opacity-50',
                    )}
                    onClick={handleRefresh}
                  />
                </CommonTooltip>
              )}
              {onExpand && (
                <CommonTooltip
                  content="Expand to full screen"
                  toolTipContentProps={{ sideOffset: 8 }}
                >
                  <ArrowExpandIcon className="h-4 w-4 cursor-pointer" onClick={onExpand} />
                </CommonTooltip>
              )}
              {onExport && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button className="flex items-center gap-1 rounded px-2 py-1 text-sm hover:bg-gray-100 dark:hover:bg-gray-800">
                      <DownloadIcon className="h-4 w-4" />
                      <span>Export Trace</span>
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={onExport}>
                      <FileDown className="mr-2 h-4 w-4" />
                      Download as JSON
                    </DropdownMenuItem>
                    {onCopyJson && (
                      <DropdownMenuItem onClick={onCopyJson}>
                        <Copy className="mr-2 h-4 w-4" />
                        Copy JSON to clipboard
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>
        </div>

        {stickyContent && (
          <div className="sticky top-[calc(2.5rem+1px)] z-10 border-b border-gray-200 bg-[#F7F8FF] p-4 pb-0 dark:border-gray-700 dark:bg-slate-900">
            {stickyContent}
          </div>
        )}
        <div className="flex-1 overflow-hidden">{children}</div>
      </div>
    </DismissableLayer>
  );
};
