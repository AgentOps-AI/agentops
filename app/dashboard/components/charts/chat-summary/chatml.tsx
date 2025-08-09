import { chatmlPrompt } from '@/lib/interfaces';
import { titleCase, truncateString } from '@/lib/utils';
import Image from 'next/image';
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

const renderMessageContent = (content: string) => {
  const codeBlockRegex = /^([\s\S]*?)```(\w*)\n([\s\S]*?)```([\s\S]*)$/;
  const match = content.match(codeBlockRegex);

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
        {content}
      </ReactMarkdown>
    );
  }
};

export function ChatmlPrompt({
  chatmlPrompt,
  truncationLength,
  role,
}: {
  chatmlPrompt: chatmlPrompt;
  truncationLength?: number;
  role?: 'user' | 'system' | 'tool';
}) {
  return (
    <>
      {chatmlPrompt.messages
        .filter((m) => (role ? m.role === role : true))
        .map((message, index) => {
          const roleTitle = role ? '' : titleCase(message.role);
          let message_text: string = '';
          const image_urls: string[] = [];

          if (typeof message.content === 'string') {
            message_text = truncateString(message.content, truncationLength);
          } else if (Array.isArray(message.content)) {
            message.content.forEach((item) => {
              if (item.type === 'text') {
                message_text = truncateString(item.text, truncationLength);
              } else if (item.type === 'image_url') {
                image_urls.push(item.image_url.url);
              }
            });
          }

          return (
            <ChatmlMessage
              key={index}
              message_text={message_text}
              image_urls={image_urls}
              role={roleTitle}
            />
          );
        })}
    </>
  );
}

function ChatmlImage({ image_urls }: { image_urls: string[] | null | undefined }) {
  if (!image_urls || image_urls.length === 0) {
    return <></>;
  }

  return (
    <div className="flex gap-4">
      {image_urls?.map((image_url, index) => (
        <div
          key={index}
          style={{ position: 'relative', width: '150px', height: '150px' }}
          className="bg-slate-200"
        >
          <Image
            src={image_url}
            alt="Image sent to GPT-4V"
            sizes="150px"
            fill
            style={{
              objectFit: 'contain',
            }}
            className="p-2"
          />
        </div>
      ))}
    </div>
  );
}

export function ChatmlMessage({
  role,
  message_text,
  image_urls,
}: {
  role?: string;
  message_text: string;
  image_urls?: string[];
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-col gap-1">
        {role && <div className="font-semibold text-[#191222] dark:text-white">{role}:</div>}
        <div className="min-w-0 break-words font-medium text-secondary dark:text-white">
          {renderMessageContent(message_text)}
        </div>
      </div>
      <ChatmlImage image_urls={image_urls} />
    </div>
  );
}
