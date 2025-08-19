import React, { useState } from 'react';
import json5 from 'json5';
import {
  ChevronDown,
  ChevronRight,
  Clock,
  Settings,
  MessageSquare,
  Zap,
  FileText,
  Activity,
} from 'lucide-react';
import { ISpan } from '@/types/ISpan';
import CustomTabs from '@/components/ui/custom-tabs';
import { UnifiedToolSpanViewer, extractUnifiedToolData } from './event-visualizers/tool-span';
import MonacoEditor from '@monaco-editor/react';
import { FormattedTokenDisplay } from '@/components/ui/formatted-token-display';
import { getIconForModel } from '@/lib/modelUtils';
import { TruncatedMessageViewer } from '@/components/ui/truncated-message-viewer';

const SpanAttributesViewer = ({
  span,
  showHeader = true,
}: {
  span: ISpan;
  showHeader?: boolean;
}) => {
  const [expandedSections, setExpandedSections] = useState({
    general: true,
    prompts: false,
    completion: false,
    usage: true,
    tool: false,
  });

  const toggleSection = (section: any) => {
    setExpandedSections({
      ...expandedSections,
      // @ts-expect-error - Dynamic key access
      [section]: !expandedSections[section],
    });
  };

  // Format duration from nanoseconds to ms or seconds
  const formatDuration = (nanoseconds: string = '0') => {
    const milliseconds = parseInt(nanoseconds || '0') / 1000000;
    return milliseconds >= 1000
      ? `${(milliseconds / 1000).toFixed(2)}s`
      : `${milliseconds.toFixed(2)}ms`;
  };

  const renderSpanCard = (span: ISpan, mainKey: string) => {
    if (!span) return null;

    const spanAttributes = span?.span_attributes ?? {};
    const genAi = spanAttributes?.gen_ai ?? {};
    const _llm = spanAttributes?.llm ?? {};
    const messages = genAi?.prompt
      ? typeof genAi?.prompt === 'string'
        ? convertToObject(genAi?.prompt ?? '[]')
        : genAi?.prompt
      : [];
    const completions = genAi?.completion
      ? typeof genAi?.completion === 'string'
        ? convertToObject(genAi?.completion ?? '[]')
        : genAi?.completion
      : [];

    return (
      <div
        key={span?.span_id ?? mainKey}
        className="sticky top-[54px] mb-6 overflow-hidden rounded-lg bg-white shadow-md"
      >
        {showHeader && (
          <div className="flex items-center justify-between bg-indigo-600 p-2 text-white">
            <div className="flex items-center">
              <MessageSquare className="mr-2" size={20} />
              <h2 className="text-lg font-semibold dark:text-gray-700">OpenAI Chat Session</h2>
            </div>
            <div className="flex items-center text-sm">
              <span className="rounded-full bg-indigo-700 px-3 py-1">
                {genAi.request?.model || 'Unknown Model'}
              </span>
            </div>
          </div>
        )}

        <div className="border-b border-gray-200">
          <div
            className="flex cursor-pointer items-center p-2 hover:bg-gray-50"
            onClick={() => toggleSection('general')}
          >
            <Settings size={16} className="mr-2 text-gray-500" />
            <h3 className="font-medium text-gray-700">General Info | {span.span_type}</h3>
            {expandedSections.general ? (
              <ChevronDown size={16} className="ml-2 text-gray-500" />
            ) : (
              <ChevronRight size={16} className="ml-2 text-gray-500" />
            )}
          </div>

          {expandedSections?.general && (
            <div className="grid grid-cols-3 gap-2 bg-gray-50 p-2 pt-0">
              <div className="col-span-1">
                <div className="text-sm">
                  <p className="text-gray-500">Span ID</p>
                  <p className="mt-1 truncate font-mono text-xs dark:text-gray-700">
                    {span?.span_id}
                  </p>
                </div>
              </div>
              <div className="col-span-1">
                <div className="text-sm">
                  <p className="text-gray-500">System</p>
                  <p className="mt-1 flex items-center font-mono font-medium dark:text-gray-700">
                    {getIconForModel(genAi?.system || '') ? (
                      <span className="mr-1 h-4 w-4">{getIconForModel(genAi?.system || '')}</span>
                    ) : null}
                    {genAi?.system || 'N/A'}
                  </p>
                </div>
              </div>
              <div className="col-span-1">
                <div className="text-sm">
                  <p className="text-gray-500">Duration</p>
                  <div className="mt-1 flex items-center truncate font-mono text-xs dark:text-gray-700">
                    <Clock size={14} className="mr-1 text-gray-400 dark:text-gray-700" />
                    <p>{formatDuration(`${span?.duration || '0'}`)}</p>
                  </div>
                </div>
              </div>
              <div className="col-span-1">
                <div className="text-sm">
                  <p className="text-gray-500">API Base</p>
                  <p className="mt-1 truncate font-mono text-xs dark:text-gray-700">
                    {genAi?.openai?.api_base || 'N/A'}
                  </p>
                </div>
              </div>
              <div className="col-span-1">
                <div className="text-sm">
                  <p className="text-gray-500">Response ID</p>
                  <p className="mt-1 truncate font-mono text-xs dark:text-gray-700">
                    {genAi?.response?.[0]?.id || 'N/A'}
                  </p>
                </div>
              </div>
              <div className="col-span-1">
                <div className="text-sm">
                  <p className="text-gray-500">Response Model</p>
                  <p className="mt-1 truncate font-mono text-xs dark:text-gray-700">
                    {checkResponseModel(genAi?.response)}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {span?.span_attributes?.tool == undefined && completions && completions?.length > 0 && (
          <div className="border-b border-gray-200">
            <div
              className="flex cursor-pointer items-center p-2 hover:bg-gray-50"
              onClick={() => toggleSection('usage')}
            >
              <Activity size={16} className="mr-2 text-gray-500" />
              <h3 className="font-medium text-gray-700">Usage Statistics</h3>
              {expandedSections?.usage ? (
                <ChevronDown size={16} className="ml-2 text-gray-500" />
              ) : (
                <ChevronRight size={16} className="ml-2 text-gray-500" />
              )}
            </div>

            {expandedSections?.usage && (
              <div className="bg-gray-50 p-2 pt-2">
                {(() => {
                  const promptTokens = parseInt(genAi.usage?.prompt_tokens || '0');
                  const completionTokens = parseInt(genAi.usage?.completion_tokens || '0');
                  const totalTokens = promptTokens + completionTokens;

                  return (
                    <>
                      <div className="mb-4 flex items-center space-x-8">
                        <div className="text-center">
                          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
                            <Zap size={20} className="text-blue-600" />
                          </div>
                          <p className="text-sm text-gray-500">Prompt</p>
                          <FormattedTokenDisplay value={promptTokens} className="justify-center" />
                        </div>

                        <div className="text-center">
                          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                            <MessageSquare size={20} className="text-green-600" />
                          </div>
                          <p className="text-sm text-gray-500">Completion</p>
                          <FormattedTokenDisplay
                            value={completionTokens}
                            className="justify-center"
                          />
                        </div>

                        <div className="text-center">
                          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-purple-100">
                            <FileText size={20} className="text-purple-600" />
                          </div>
                          <p className="text-sm text-gray-500">Total</p>
                          <FormattedTokenDisplay value={totalTokens} className="justify-center" />
                        </div>
                      </div>

                      <div className="mt-4">
                        <div className="h-2.5 w-full rounded-full bg-gray-200">
                          <div className="flex h-2.5 rounded-full">
                            <div
                              className="h-2.5 rounded-l-full bg-blue-600"
                              style={{
                                width: `${(promptTokens / totalTokens) * 100}%`,
                              }}
                            ></div>
                            <div
                              className="h-2.5 rounded-r-full bg-green-500"
                              style={{
                                width: `${(completionTokens / totalTokens) * 100}%`,
                              }}
                            ></div>
                          </div>
                        </div>
                        <div className="mt-1 flex justify-between text-xs text-gray-500 dark:text-gray-700">
                          <span>Prompt: {((promptTokens / totalTokens) * 100).toFixed(1)}%</span>
                          <span>
                            Completion: {((completionTokens / totalTokens) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </>
                  );
                })()}
              </div>
            )}
          </div>
        )}

        {messages !== undefined && messages?.length > 0 && (
          <div className="border-b border-gray-200">
            <div
              className="flex cursor-pointer items-center p-2 hover:bg-gray-50"
              onClick={() => toggleSection('prompts')}
            >
              <MessageSquare size={16} className="mr-2 text-gray-500" />
              <h3 className="font-medium text-gray-700">Conversation</h3>
              <span className="ml-2 rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-700">
                {messages?.length} messages
              </span>
              {expandedSections.prompts ? (
                <ChevronDown size={16} className="ml-2 text-gray-500" />
              ) : (
                <ChevronRight size={16} className="ml-2 text-gray-500" />
              )}
            </div>

            {expandedSections.prompts && (
              <div className="space-y-3 p-2">
                {messages?.map((message: any, idx: number) => {
                  const messageRole = message.role || 'assistant';
                  return (
                    <div key={idx} className="rounded-lg border p-2">
                      <TruncatedMessageViewer
                        data={[message]}
                        type={messageRole as 'user' | 'assistant' | 'system' | 'tool'}
                        role={messageRole === 'user' ? undefined : messageRole as 'assistant' | 'system' | 'tool'}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {span.span_attributes.tool !== undefined && (
          <div>
            <div
              className="flex cursor-pointer items-center p-2 hover:bg-gray-50"
              onClick={() => toggleSection('tool')}
            >
              <MessageSquare size={16} className="mr-2 text-gray-500" />
              <div className="flex w-full items-center justify-between">
                <div className="font-medium text-gray-700">Tool</div>
                <div className="flex items-center space-x-2">
                  <div
                    className={`rounded-full px-3 py-1 ${span.span_attributes.tool.status === 'failed' ? 'bg-red-700' : 'bg-green-700'} flex items-center text-xs text-white`}
                  >
                    <span className="ml-1 capitalize">{span.span_attributes.tool.status}</span>
                  </div>
                  <div className="flex items-center rounded-full bg-opacity-20 py-1 text-sm">
                    <Clock size={14} className="mr-1" />
                    <span>{extractUnifiedToolData(span)?.duration?.toFixed(2) ?? '0.00'}ms</span>
                  </div>
                </div>
              </div>
            </div>

            {expandedSections.tool && <UnifiedToolSpanViewer toolSpan={span} />}
          </div>
        )}

        {completions && completions?.length > 0 && (
          <div>
            <div
              className="flex cursor-pointer items-center p-2 hover:bg-gray-50"
              onClick={() => toggleSection('completion')}
            >
              <MessageSquare size={16} className="mr-2 text-gray-500 dark:text-gray-700" />
              <h3 className="font-medium text-gray-700">Completion</h3>
              {expandedSections.completion ? (
                <ChevronDown size={16} className="ml-2 text-gray-500 dark:text-gray-700" />
              ) : (
                <ChevronRight size={16} className="ml-2 text-gray-500 dark:text-gray-700" />
              )}
            </div>

            {expandedSections.completion && (
              <div className="p-2">
                {completions.map((completion: any, idx: number) => {
                  const innerItemsArray = Object.keys(completion).map((key: any) => {
                    return completion[key];
                  });

                  return (
                    <div key={idx} className="rounded-lg border border-green-200 bg-green-50 p-2">
                      {innerItemsArray.map((item: any, ind: number) => {
                        const itemRole = item.role || 'assistant';
                        return (
                          <div key={ind}>
                            <TruncatedMessageViewer
                              data={[item]}
                              type={itemRole as 'user' | 'assistant' | 'system' | 'tool'}
                              role={itemRole === 'user' ? undefined : itemRole as 'assistant' | 'system' | 'tool'}
                            />
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="h-full">
      <CustomTabs
        tabs={[
          {
            value: 'general-info',
            label: 'Pretty',
            content: renderSpanCard(span, 'span-card'),
          },
          {
            value: 'raw-data',
            label: 'Raw Data',
            content: (
              <>
                <div className="overflow-hidden rounded-lg border border-gray-200">
                  <MonacoEditor
                    height="83vh"
                    width="100%"
                    language="json"
                    theme="vs-dark"
                    options={{
                      tabSize: 1,
                      insertSpaces: false,
                      readOnly: true,
                      minimap: { enabled: false },
                      scrollBeyondLastLine: false,
                      padding: { top: 16, bottom: 16 },
                      roundedSelection: true,
                      smoothScrolling: true,
                    }}
                    value={(() => {
                      try {
                        return JSON.stringify(span, null, 2);
                      } catch (error) {
                        // If JSON stringify fails, return the original value or a string representation
                        return typeof span === 'string' ? span : String(span);
                      }
                    })()}
                  />
                </div>
              </>
            ),
          },
        ]}
        defaultValue="general-info"
      />
    </div>
  );
};

export default SpanAttributesViewer;

export const convertToObject = (data: string) => {
  if (typeof data !== 'string') return data;
  let parsedData;
  try {
    parsedData = json5.parse(data);
  } catch (error) {
    try {
      parsedData = parseConversationString(data);
    } catch (parseError) {
      console.error('[convertToObject] Failed to parse data:', parseError);
      // Return empty array as fallback instead of throwing
      return [];
    }
  }
  return parsedData;
};

export function parseConversationString(str: string) {
  try {
    // Step 1: Complete the string if it's cut off
    // This assumes the string is an array that might be cut off
    let completeStr = str;
    if (!completeStr.endsWith(']')) {
      // Count opening and closing brackets to determine if we need to add a closing bracket
      const openBrackets = (completeStr.match(/\[/g) || []).length;
      const closeBrackets = (completeStr.match(/\]/g) || []).length;

      if (openBrackets > closeBrackets) {
        completeStr += '}]';
      }
    }

    // Step 2: Convert to valid JSON
    // Handle the single quotes appropriately

    // First, replace property names (keys with single quotes)
    completeStr = completeStr.replace(/'([^']+)':/g, '"$1":');

    // Handle string values with single quotes that DON'T contain escaped characters
    completeStr = completeStr.replace(/: '([^'\\]*?)'/g, ': "$1"');

    // Handle nested structures with array brackets
    completeStr = completeStr.replace(/\['([^']+)'\]/g, '["$1"]');

    // Handle remaining single quoted strings, being careful with nested quotes
    let result = '';
    let inSingleQuotes = false;
    let currentToken = '';

    for (let i = 0; i < completeStr.length; i++) {
      const char = completeStr[i];
      const nextChar = completeStr[i + 1] || '';

      if (char === "'" && (i === 0 || completeStr[i - 1] !== '\\')) {
        if (inSingleQuotes) {
          // Closing quote - add the token with double quotes
          result += '"' + currentToken + '"';
          currentToken = '';
          inSingleQuotes = false;
        } else {
          // Opening quote
          inSingleQuotes = true;
        }
      } else if (inSingleQuotes) {
        // Inside quotes - escape double quotes and backslashes
        if (char === '"') {
          currentToken += '\\"';
        } else if (char === '\\' && nextChar === "'") {
          // Skip the escape for single quote
          currentToken += "'";
          i++; // Skip the next character (the single quote)
        } else {
          currentToken += char;
        }
      } else {
        result += char;
      }
    }

    // Add any remaining token
    if (currentToken) {
      result += currentToken;
    }

    // Final cleanup - ensure commas are correct in arrays
    result = result.replace(/}(?=\s*{)/g, '},');

    // Parse the fixed string
    return JSON.parse(result);
  } catch (error) {
    console.error('Parsing error:', error);

    // Alternative approach: use Function constructor (safer than eval)
    try {
      // Add array brackets if not present
      if (!str.trim().startsWith('[')) {
        str = '[' + str;
      }
      if (!str.trim().endsWith(']')) {
        str = str + ']';
      }

      // Convert to valid JavaScript syntax
      const jsString = str
        .replace(/'/g, '"') // Replace all single quotes with double quotes
        .replace(/"([^"]+)":/g, '$1:') // Fix property names
        .replace(/([{,]\s*)(\w+):/g, '$1"$2":'); // Ensure all keys are quoted

      return Function('"use strict"; return ' + jsString)();
    } catch (fallbackError) {
      console.error('Alternative parsing failed:', fallbackError);
      // Return empty array instead of null to prevent errors
      return [];
    }
  }
}

const checkResponseModel = (response: any): string => {
  return Array.isArray(response) ? response[0]?.model : response?.model ? response.model : 'N/A';
};
