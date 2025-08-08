'use client';
import json5 from 'json5';
import { TruncatedMessageViewer } from '@/components/ui/truncated-message-viewer';
import { ILlms, completion, prompt } from '@/lib/interfaces';
import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { ReadOnlyCodeViewer } from '@/components/ui/read-only-code-viewer';

// Helper function to map short codes to Monaco languages
const mapLanguage = (lang: string | undefined): string => {
  if (!lang) return 'plaintext';
  const lowerLang = lang.toLowerCase();
  switch (lowerLang) {
    case 'py':
      return 'python';
    case 'js':
      return 'javascript';
    case 'ts':
      return 'typescript';
    case 'html':
      return 'html';
    case 'css':
      return 'css';
    case 'json':
      return 'json';
    case 'sql':
      return 'sql';
    default:
      return lowerLang;
  }
};

export const renderMessageContent = (content: string) => {
  let contentToRender = content;
  try {
    const parsedContent = json5.parse(content);
    contentToRender = parsedContent.map((p: any) => p?.content || p?.text).join('');
  } catch (e) {
    // If parsing fails, use the original content
    contentToRender = content;
  }

  const codeBlockRegex = /^([\s\S]*?)```(\w*)\n([\s\S]*?)```([\s\S]*)$/;
  const match = contentToRender.match(codeBlockRegex);

  if (match) {
    const [, beforeText, lang, code, afterText] = match;
    const monacoLang = mapLanguage(lang);
    return (
      <>
        {beforeText && (
          <ReactMarkdown className="prose prose-sm dark:prose-invert max-w-none">
            {beforeText.trim()}
          </ReactMarkdown>
        )}
        <ReadOnlyCodeViewer
          language={monacoLang}
          value={code.trim()}
          height="180px"
          title="code snippet"
          className="my-2"
        />
        {afterText && (
          <ReactMarkdown className="prose prose-sm dark:prose-invert max-w-none">
            {afterText.trim()}
          </ReactMarkdown>
        )}
      </>
    );
  } else {
    return (
      <ReactMarkdown className="prose prose-sm dark:prose-invert max-w-none">
        {contentToRender}
      </ReactMarkdown>
    );
  }
};

export function LLMChatViewer({ llmEvents }: { llmEvents: ILlms[] }) {
  const filteredEvents = useMemo(
    () => llmEvents.filter((llmEvent) => llmEvent.type === 'LLM Call'),
    [llmEvents],
  );

  return (
    <div className="mt-8">
      {filteredEvents.map((llm, i) => {
        const hasToolMessage =
          llm.prompt.type === 'chatml' &&
          llm.prompt.messages.some((message) => message.role === 'tool' && message.content !== '');

        const hasSystemMessage =
          llm.prompt.type === 'chatml' &&
          llm.prompt.messages.some(
            (message) => message.role === 'system' && message.content !== '',
          );

        const hasUserMessage =
          (llm.prompt.type === 'chatml' &&
            llm.prompt.messages.some(
              (message) => message.role === 'user' && message.content !== '',
            )) ||
          llm.prompt.type === 'string';

        return (
          <div key={i} className="px-40 text-sm">
            {hasSystemMessage && (
              <div className="relative flex items-start gap-2">
                <TruncatedMessageViewer data={[llm.prompt]} type="system" role="system" />
              </div>
            )}
            {hasToolMessage && (
              <div className="relative flex items-start gap-2">
                <TruncatedMessageViewer data={[llm.prompt]} type="tool" role="tool" />
              </div>
            )}
            {hasUserMessage && (
              <div className="relative flex items-start justify-end gap-2">
                <TruncatedMessageViewer data={[llm.prompt]} type="user" />
              </div>
            )}
            <div className="relative flex items-start gap-2">
              <TruncatedMessageViewer data={[llm.completion]} type="assistant" role="assistant" />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function FormattedCompletion({
  completion,
  truncationLength,
  hideRole = false,
}: {
  completion: completion;
  truncationLength?: number;
  hideRole?: boolean;
}) {
  if (!completion) return <></>;

  // Instead of custom rendering, wrap in TruncatedMessageViewer
  return (
    <div className="w-full">
      <TruncatedMessageViewer data={[completion]} type="assistant" role="assistant" />
    </div>
  );
}

export function FormattedPrompt({
  prompts,
  truncationLength,
  role = 'user',
}: {
  prompts: any[];
  truncationLength?: number;
  role?: 'user' | 'system' | 'tool';
}) {
  if (!prompts || !prompts.length) return null;

  // Process prompts to ensure they're in a format ChatViewerRuntimeProvider can handle
  const processedPrompts = prompts.map(prompt => {
    // If prompt is already in the correct format with role and content, keep it as is
    if (prompt && typeof prompt === 'object' && 'role' in prompt && 'content' in prompt) {
      return prompt;
    }

    // If it's a user_query, convert it to the right format
    if (prompt && typeof prompt === 'object' && 'user_query' in prompt) {
      return {
        role: 'user',
        content: prompt.user_query
      };
    }

    // Try to extract any text content
    let content = '';
    if (typeof prompt === 'string') {
      content = prompt;
    } else if (prompt && typeof prompt === 'object') {
      if ('string' in prompt && typeof prompt.string === 'string') {
        content = prompt.string;
      } else if ('text' in prompt && typeof prompt.text === 'string') {
        content = prompt.text;
      }
    }

    return {
      role: role,
      content: content
    };
  });

  // Instead of custom rendering, wrap in TruncatedMessageViewer
  return (
    <div className="w-full">
      <TruncatedMessageViewer
        data={processedPrompts}
        type={role}
        role={role === 'user' ? undefined : role}
      />
    </div>
  );
}

export default LLMChatViewer;
