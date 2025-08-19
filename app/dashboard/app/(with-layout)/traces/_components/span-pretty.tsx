import React from 'react';
import { ISpan } from '@/types/ISpan';
import { convertToObject } from './span-attribute-viewer';
import { cn } from '@/lib/utils';
import { TruncatedMessageViewer } from '@/components/ui/truncated-message-viewer';

type SpanPrettyProps = {
  selectedSpan: ISpan | null;
};

export const SpanPretty = ({ selectedSpan }: SpanPrettyProps) => {
  const { processedCompletions } = useProcessedCompletions(selectedSpan);
  const processedPrompts = useProcessedPrompts(selectedSpan);

  if (!selectedSpan) {
    return (
      <div className="col-span-3 flex h-full min-h-0 items-center justify-center rounded-md border border-dashed text-gray-500 dark:border-slate-700">
        Select a span in the chart to view details.
      </div>
    );
  }

  const spanAttributes = selectedSpan?.span_attributes ?? {};
  const genAi = spanAttributes?.gen_ai ?? {};
  const isLlmSpan = !!genAi;

  if (!isLlmSpan) {
    // Non-LLM spans are handled by the full-width raw view in the parent
    return null;
  }

  if (processedCompletions.length === 0 && processedPrompts.length === 0) {
    return (
      <div className="col-span-3 h-full min-h-0 overflow-y-auto rounded-md border border-gray-200 p-3 dark:border-slate-700">
        <div className="pt-4 text-center text-sm text-gray-500">
          No completion data found for this span.
        </div>
      </div>
    );
  }

  return (
    <div className="h-full min-h-0" data-testid="trace-detail-span-pretty-content">
      <div className="space-y-4">
        <div className={cn('mt-6 px-2')}>
          <div className="mt-1 space-y-2 text-sm">
            {processedPrompts.map((msg, index) => (
              <div key={index} className="py-1">
                <TruncatedMessageViewer
                  data={[msg]}
                  type={msg.role}
                  role={msg.role === 'user' ? undefined : msg.role as 'assistant' | 'system' | 'tool'}
                />
              </div>
            ))}
          </div>
          {processedCompletions.length > 0 && (
            <div>
              <div className="text-sm">
                {processedCompletions.map((msg, index) => (
                  <div key={index} className="py-1">
                    <TruncatedMessageViewer
                      data={[msg]}
                      type={msg.role || 'assistant'}
                      role={msg.role === 'user' ? undefined : (msg.role || 'assistant') as 'assistant' | 'system' | 'tool'}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Hook for processing prompts to handle the unique structure
const useProcessedPrompts = (selectedSpan: ISpan | null) => {
  const spanAttributes = selectedSpan?.span_attributes ?? {};
  const genAi = spanAttributes?.gen_ai ?? {};

  return React.useMemo(() => {
    if (!genAi?.prompt) return [];

    try {
      const promptData =
        typeof genAi.prompt === 'string' ? convertToObject(genAi.prompt) : genAi.prompt;

      const promptArray = Array.isArray(promptData) ? promptData : [promptData];

      // Normalize various possible prompt structures into { role, content }
      return promptArray
        .map((item) => {
          if (!item) return null;

          // Case 1: already in the form { content, role? }
          if (typeof item === 'object' && 'content' in item) {
            return {
              ...item,
              role: 'role' in item ? (item as any).role : 'user',
            };
          }

          // Case 2: { index: { content, role? } }
          if (typeof item === 'object') {
            const key = Object.keys(item)[0];
            const messageObj = (item as any)[key];
            if (messageObj && typeof messageObj === 'object' && 'content' in messageObj) {
              return {
                ...messageObj,
                role: 'role' in messageObj ? messageObj.role : 'user',
              };
            }
          }

          // Case 3: plain string prompt
          if (typeof item === 'string') {
            return { content: item, role: 'user' };
          }

          return null;
        })
        .filter(Boolean);
    } catch (error) {
      console.error('Error processing prompt data:', error);
      return [];
    }
  }, [genAi?.prompt]);
};

// Hook for processing completions to keep main component cleaner
const useProcessedCompletions = (selectedSpan: ISpan | null) => {
  const spanAttributes = selectedSpan?.span_attributes ?? {};
  const genAi = spanAttributes?.gen_ai ?? {};

  const rawCompletions = React.useMemo(() => {
    if (!genAi?.completion) return [];
    try {
      const completionData = genAi.completion;
      if (typeof completionData === 'string') {
        const parsed = convertToObject(completionData);
        return Array.isArray(parsed) ? parsed : [parsed];
      }
      return Array.isArray(completionData) ? completionData : [completionData];
    } catch (error) {
      console.error('Error processing completion data:', error);
      return [];
    }
  }, [genAi?.completion]);

  const processedCompletions = React.useMemo(() => {
    return rawCompletions
      .map((item) => {
        // First check if the item itself has tool_calls directly (new format)
        if (item && item.tool_calls && Array.isArray(item.tool_calls)) {
          const messages = [];

          // If there's also assistant content with the tool calls, add it first
          if (item.content) {
            messages.push({
              role: item.role || 'assistant',
              content: item.content
            });
          }

          // Process each tool call
          item.tool_calls.forEach((toolCall: any) => {
            // Handle direct tool call format with 'arguments' and 'name'
            if (toolCall.name) {
              let formattedContent = `🔧 Function Call: ${toolCall.name}\n`;

              if (toolCall.arguments) {
                try {
                  // Try to parse and pretty-print the arguments if they're JSON
                  const args = typeof toolCall.arguments === 'string'
                    ? JSON.parse(toolCall.arguments)
                    : toolCall.arguments;
                  formattedContent += `Arguments:\n${JSON.stringify(args, null, 2)}`;
                } catch {
                  // If parsing fails, just show the raw arguments
                  formattedContent += `Arguments: ${toolCall.arguments}`;
                }
              }

              messages.push({
                role: 'tool',
                content: formattedContent
              });
            } else {
              // Fallback for other tool call formats
              messages.push({
                role: 'tool',
                content: typeof toolCall === 'object'
                  ? JSON.stringify(toolCall, null, 2)
                  : String(toolCall)
              });
            }
          });

          return messages;
        }

        // Original logic for nested structure
        const key = Object.keys(item)[0];
        const content = key ? item[key] : item;

        // Check if this contains tool calls in the nested structure
        if (content && content.tool_calls && Array.isArray(content.tool_calls)) {
          // Extract tool calls and format them for display
          return content.tool_calls
            .map((toolCallObj: Record<string, any>) => {
              const toolCallKey = Object.keys(toolCallObj)[0];
              const toolCall = toolCallObj[toolCallKey];

              if (toolCall) {
                return {
                  role: 'tool',
                  content:
                    typeof toolCall === 'object'
                      ? JSON.stringify(toolCall, null, 2)
                      : String(toolCall),
                };
              }
              return null;
            })
            .filter(Boolean);
        }

        // Handle regular assistant messages
        if (content) {
          return {
            role: content.role || 'assistant',
            content:
              content.content ||
              (typeof content === 'string'
                ? content
                : typeof content === 'object'
                  ? JSON.stringify(content, null, 2)
                  : String(content)),
          };
        }

        return null;
      })
      .flat()
      .filter(Boolean);
  }, [rawCompletions]);

  return { processedCompletions };
};
