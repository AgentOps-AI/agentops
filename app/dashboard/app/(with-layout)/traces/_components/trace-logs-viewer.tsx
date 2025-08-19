import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { fetchAuthenticatedApi, ApiError } from '@/lib/api-client';
import { CodeBlock } from '@/components/ui/code-block';
import { sanitize } from 'isomorphic-dompurify';
import { ansiToHtml, stripAnsiCodes } from '@/utils/ansi-to-html.util';
import { cn } from '@/lib/utils';
import { Checkbox } from '@/components/ui/checkbox';
import { useOrgFeatures } from '@/hooks/useOrgFeatures';
import { InformationCircleIcon as InfoIcon } from 'hugeicons-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

function removeMetadataFromRaw(content: string): string {
  // Regex to match an ANSI escape code (non-capturing group)
  const ansiCode = '(?:\\x1b\\[[0-9;]*m)?';

  // Pattern to match log entry start: timestamp - LEVEL - content
  // This regex now explicitly includes optional ANSI code patterns
  // between each component of the metadata to correctly identify it
  // even when colors are embedded.
  const pattern = new RegExp(
    `^` +
      ansiCode + // Optional ANSI code at start of line
      `(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2},\\d{3})` + // Timestamp
      ansiCode + // Optional ANSI code after timestamp
      ` - ` +
      ansiCode + // Optional ANSI code before level
      `([A-Z]+)` + // Level
      ansiCode + // Optional ANSI code after level
      ` - `,
  );

  return content
    .split('\n')
    .map((line) => line.replace(pattern, ''))
    .join('\n');
}

interface Log {
  timestamp: string;
  level: string;
  content: string;
}

interface TraceLogsViewerProps {
  traceId: string | null;
}

function logContentToHtml(content: string): string {
  let html = ansiToHtml(content);
  html = html.replace(/\n/g, '<br/>');
  return html;
}

/**
 * Parse raw log content into structured Log objects
 */
function parseLogContent(rawContent: string): Log[] {
  const logContent = prepareLogContent(rawContent);

  const lines = logContent.split('\n');

  // Remove any leading lines that don't match our log pattern
  const logStartPattern = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}/;
  while (lines.length && !logStartPattern.test(lines[0])) {
    lines.shift();
  }

  const logEntries: Log[] = [];
  let currentEntry: Partial<Log> = {};
  let currentContent = '';

  // Pattern to match log entry start: timestamp - LEVEL - content
  const logLinePattern = /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([A-Z]+) - (.*)$/;

  for (const line of lines) {
    const match = logLinePattern.exec(line);
    if (match) {
      if (currentEntry.timestamp) {
        logEntries.push({
          timestamp: currentEntry.timestamp!,
          level: currentEntry.level!,
          content: currentContent.trim(),
        });
        currentContent = '';
      }

      currentEntry = {
        timestamp: match[1],
        level: match[2],
      };
      currentContent = match[3];
    } else if (currentEntry.timestamp) {
      currentContent += '\n' + line;
    }
  }

  if (currentEntry.timestamp) {
    logEntries.push({
      timestamp: currentEntry.timestamp,
      level: currentEntry.level!,
      content: currentContent.trim(),
    });
  }

  return logEntries;
}

/**
 * Clean and prepare log content for parsing
 */
function prepareLogContent(rawContent: string): string {
  // Remove leading/trailing whitespace
  let content = rawContent.trim();

  // Handle JSON string format if present
  if (content.startsWith('"') && content.endsWith('"')) {
    try {
      content = JSON.parse(content);
    } catch {
      content = content
        .slice(1, -1)
        .replace(/\\r\\n/g, '\n')
        .replace(/\\n/g, '\n')
        .replace(/\\"/g, '"')
        .replace(/\\\\/g, '\\');
    }
  }
  // Handle the case where there might be quotes in the middle
  else {
    // Cut out everything before the first quote if it exists
    const firstQuoteIndex = content.indexOf('"');
    if (firstQuoteIndex > 0) {
      content = content.substring(firstQuoteIndex + 1);
    }

    // Remove any trailing quotes and everything after
    const lastQuoteIndex = content.lastIndexOf('"');
    if (lastQuoteIndex > 0 && lastQuoteIndex < content.length - 1) {
      content = content.substring(0, lastQuoteIndex);
    }

    // Replace escaped sequences
    content = content
      .replace(/\\r\\n/g, '\n')
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
      .replace(/\\\\/g, '\\');
  }

  return content;
}

/**
 * Get color class for log level badge
 */
function getLevelBadgeColor(level: string): string {
  switch (level.toUpperCase()) {
    case 'INFO':
      return 'bg-blue-500';
    case 'WARNING':
    case 'WARN':
      return 'bg-yellow-500';
    case 'ERROR':
      return 'bg-red-500';
    case 'DEBUG':
      return 'bg-gray-500';
    default:
      return 'bg-purple-500';
  }
}

export const TraceLogsViewer = ({ traceId }: TraceLogsViewerProps) => {
  const [logs, setLogs] = useState<Log[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rawContent, setRawContent] = useState<string>('');
  const [preparedDisplayContent, setPreparedDisplayContent] = useState<string>('');
  const [selectedLog, setSelectedLog] = useState<Log | null>(null);
  const [viewMode, setViewMode] = useState<'parsed' | 'raw'>('raw');
  const [isLogsTruncated, setIsLogsTruncated] = useState(false);
  const [lineCount, setLineCount] = useState(0);
  const [showMetadata, setShowMetadata] = useState(false);
  const { permissions: orgPermissions, isLoading: isPermissionsLoading } = useOrgFeatures();

  useEffect(() => {
    const fetchLogs = async () => {
      if (!traceId) return;

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetchAuthenticatedApi<{
          content: string;
          freeplan_truncated?: boolean;
        }>(`/v4/logs/${traceId}`);

        if (!response.content) {
          throw new Error('Failed to fetch logs');
        }

        setRawContent(response.content);
        setIsLogsTruncated(response.freeplan_truncated || false);
        const parsedLogs = parseLogContent(response.content);
        setLogs(parsedLogs);

        // Set initial prepared display content based on showMetadata
        if (showMetadata) {
          setPreparedDisplayContent(prepareLogContent(response.content));
        } else {
          setPreparedDisplayContent(removeMetadataFromRaw(prepareLogContent(response.content)));
        }

        // Count lines in raw content
        const lines = response.content.split('\n').length;
        setLineCount(lines);

        if (parsedLogs.length > 0) {
          setSelectedLog(parsedLogs[0]);
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setError(
            'Logs for this trace were not found. This can happen if the Python SDK failed to upload them. ' +
              'Upgrade to the latest AgentOps Python SDK and rerun your trace to capture logs.',
          );
        } else {
          setError(err instanceof Error ? err.message : 'An error occurred while fetching logs');
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchLogs();
  }, [traceId]);

  // Effect to update preparedDisplayContent when showMetadata changes
  useEffect(() => {
    if (rawContent) {
      const fullyPreparedContent = prepareLogContent(rawContent);
      if (showMetadata) {
        setPreparedDisplayContent(fullyPreparedContent);
      } else {
        setPreparedDisplayContent(removeMetadataFromRaw(fullyPreparedContent));
      }
    }
  }, [showMetadata, rawContent]);

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-40 flex-col items-center justify-center gap-2 p-4 text-center text-gray-600 dark:text-gray-400">
        <p>Unable to load logs for this trace.</p>
        <p className="text-xs">{error}</p>
      </div>
    );
  }

  if (!isLoading && rawContent.trim() === '') {
    return (
      <div className="flex h-40 items-center justify-center p-4 text-center text-gray-600 dark:text-gray-400">
        <p>No logs were found for this trace.</p>
      </div>
    );
  }

  if (!logs || logs.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center p-4 text-center text-gray-600 dark:text-gray-400">
        <p>No logs were found for this trace.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-shrink-0 items-center justify-between px-5 pb-2">
        <div className="flex-1">
          <div className="flex items-center gap-4">
            {lineCount > 0 && (
              <span className="text-xs text-gray-600 dark:text-gray-400">{lineCount} lines</span>
            )}
            {isLogsTruncated && orgPermissions?.tierName === 'free' && !isPermissionsLoading && (
              <div className="flex items-start gap-2 text-xs text-blue-700">
                <InfoIcon className="h-4 w-4 flex-shrink-0" />
                <div>
                  <span className="font-medium">
                    Log content truncated (Free plan limit: 100 lines).
                  </span>{' '}
                  <Link href="/settings/organization" className="underline hover:text-blue-800">
                    Upgrade to see full logs
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="parsed-view"
            checked={viewMode === 'parsed'}
            onCheckedChange={(checked) => setViewMode(checked ? 'parsed' : 'raw')}
          />
          <label htmlFor="parsed-view" className="cursor-pointer text-sm font-medium">
            Parsed View
          </label>
          <Checkbox
            id="show-metadata"
            checked={showMetadata}
            onCheckedChange={(checked) => setShowMetadata(!!checked)}
          />
          <label htmlFor="show-metadata" className="cursor-pointer text-sm font-medium">
            Show Metadata
          </label>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden px-4 pb-4">
        <div className="relative h-full w-full">
          {viewMode === 'parsed' ? (
            <div
              className={cn(
                'absolute inset-0 h-full w-full overflow-auto rounded-lg border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900',
                '[&::-webkit-scrollbar]:h-1.5 [&::-webkit-scrollbar]:w-1.5',
                '[&::-webkit-scrollbar-track]:bg-transparent',
                '[&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-400/50 dark:[&::-webkit-scrollbar-thumb]:bg-gray-500/50',
                '[&::-webkit-scrollbar-thumb:hover]:bg-gray-500/70 dark:[&::-webkit-scrollbar-thumb:hover]:bg-gray-400/70',
                '[scrollbar-width:thin]',
                '[scrollbar-color:rgba(156,163,175,0.5)_transparent] dark:[scrollbar-color:rgba(156,163,175,0.7)_transparent]',
              )}
            >
              <div>
                {logs.map((log, index) => (
                  <div
                    key={index}
                    onClick={() => setSelectedLog(log)}
                    className={`cursor-pointer border-b p-3 hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800 ${
                      selectedLog === log
                        ? 'border-l-4 border-l-blue-500 bg-blue-50 dark:bg-blue-900/30'
                        : ''
                    }`}
                  >
                    {showMetadata && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {log.timestamp}
                      </div>
                    )}
                    <div className="flex items-start">
                      {showMetadata && (
                        <span
                          className={`flex-shrink-0 rounded px-2 py-1 text-xs text-white ${getLevelBadgeColor(log.level)}`}
                        >
                          {log.level}
                        </span>
                      )}
                      <span
                        className={cn(
                          'break-words text-sm dark:text-gray-200',
                          showMetadata ? 'ml-2' : '',
                        )}
                      >
                        {stripAnsiCodes(log.content.replace('\\n', ''))}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              {isLogsTruncated && orgPermissions?.tierName === 'free' && !isPermissionsLoading && (
                <div className="sticky bottom-0 border-t border-gray-200 bg-gradient-to-t from-white to-white/95 p-4 text-center dark:border-gray-700 dark:from-gray-900 dark:to-gray-900/95">
                  <p className="mb-2 text-sm text-gray-600 dark:text-gray-400">
                    You&apos;ve reached the end of your available logs
                  </p>
                  <Link href="/settings/organization">
                    <Button size="sm">Upgrade for Unlimited Logs</Button>
                  </Link>
                </div>
              )}
            </div>
          ) : (
            <div className="absolute inset-0 h-full w-full">
              <CodeBlock
                copyButtonPlacement="overlay"
                dataToCopy={stripAnsiCodes(preparedDisplayContent)}
                title=""
                forceDarkMode
              >
                <div
                  className="h-full w-full overflow-auto bg-transparent"
                  dangerouslySetInnerHTML={{
                    __html: sanitize(logContentToHtml(preparedDisplayContent)),
                  }}
                />
              </CodeBlock>
              {isLogsTruncated && orgPermissions?.tierName === 'free' && !isPermissionsLoading && (
                <div className="absolute bottom-0 left-0 right-0 border-t border-gray-700 bg-gradient-to-t from-gray-900 to-gray-900/95 p-4 text-center">
                  <p className="mb-2 text-sm text-gray-400">
                    You&apos;ve reached the end of your available logs
                  </p>
                  <Link href="/settings/organization">
                    <Button size="sm">Upgrade for Unlimited Logs</Button>
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
