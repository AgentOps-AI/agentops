'use client';

import { ActionBarPrimitive, MessagePrimitive, ThreadPrimitive } from '@assistant-ui/react';
import { ThumbsDownIcon as ThumbsDown, ThumbsUpIcon as ThumbsUp } from 'hugeicons-react';
import type { FC } from 'react';
import { Avatar, AvatarFallback } from '../ui/avatar';
import { CommonTooltip } from '../ui/common-tooltip';
import { CopyButton } from '../ui/copy-button';
import { toast } from '../ui/use-toast';
import { MarkdownText } from './markdown-text';

type Role = 'assistant' | 'system' | 'tool';
const handleClick = () => {
  toast({
    title: 'Evals coming soon for Pro plan users!',
  });
};

export const Thread = ({ role = 'assistant' }: { role?: Role }) => {
  return (
    <ThreadPrimitive.Root className="h-full overflow-hidden bg-transparent">
      <ThreadPrimitive.Viewport className="flex h-full flex-col items-center bg-inherit px-4">
        <ThreadPrimitive.Messages
          components={{
            UserMessage: UserMessage,
            AssistantMessage: (props) => <AssistantMessage {...props} role={role} />,
          }}
        />

        <div className="min-h-2 flex-grow" />
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
};

const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="grid w-full auto-rows-auto gap-y-2 py-1">
      <div className="col-start-2 row-start-1 max-w-[90%] justify-self-end overflow-x-auto break-words rounded-3xl bg-[#E1E2F27D] px-5 py-2.5 text-slate-950 dark:bg-slate-800 dark:text-slate-50">
        <MessagePrimitive.Content components={{ Text: MarkdownText }} />
      </div>
    </MessagePrimitive.Root>
  );
};

const AssistantMessage = ({ role }: { role?: Role }) => {
  let tooltip = 'Assistant';
  let fallback = 'A';

  if (role === 'system') {
    tooltip = 'System';
    fallback = 'S';
  } else if (role === 'tool') {
    tooltip = 'Tool';
    fallback = 'T';
  }
  return (
    <MessagePrimitive.Root className="relative grid w-full grid-cols-[auto_1fr] grid-rows-[auto_1fr] px-1 py-1">
      <CommonTooltip content={tooltip}>
        <Avatar className="col-start-1 row-span-full row-start-1 mr-4 cursor-pointer">
          <AvatarFallback className="bg-[#141b34ad] text-white">{fallback}</AvatarFallback>
        </Avatar>
      </CommonTooltip>
      <div className="assistant-message-content col-start-2 row-start-1 my-1.5 break-words text-slate-950 dark:text-slate-50">
        <MessagePrimitive.Content components={{ Text: MarkdownText }} />
      </div>
      <AssistantActionBar />
    </MessagePrimitive.Root>
  );
};

const AssistantActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      autohideFloat="single-branch"
      className="col-start-2 row-start-2 -ml-1 flex items-center gap-2 text-primary data-[floating]:absolute data-[floating]:rounded-md data-[floating]:border data-[floating]:bg-white data-[floating]:p-1 data-[floating]:shadow-sm dark:text-slate-400 dark:data-[floating]:bg-slate-950"
    >
      <CopyButton
        iconSize={18}
        iconStrokeWidth={1.5}
        iconStrokeOpacity="0.68"
        onClick={async () => {
          const messageElement = document.querySelector(
            '.assistant-message-content',
          ) as HTMLElement;
          if (messageElement) {
            const textToCopy = messageElement.innerText;
            await copyToClipboard(textToCopy);
          }
        }}
      />
      <ThumbsUp
        className="cursor-pointer duration-300 ease-in-out hover:scale-125 active:mt-1.5"
        size={18}
        onClick={handleClick}
        strokeWidth={1.5}
        strokeOpacity="0.68"
      />
      <ThumbsDown
        className="cursor-pointer duration-300 ease-in-out hover:scale-125 active:mt-1.5"
        size={18}
        strokeWidth={1.5}
        strokeOpacity="0.68"
        onClick={handleClick}
      />
    </ActionBarPrimitive.Root>
  );
};

async function copyToClipboard(textToCopy: string | undefined) {
  if (!textToCopy) return;
  try {
    await navigator.clipboard.writeText(textToCopy);
    toast({
      title: 'Copied to Clipboard',
    });
  } catch (error) {
    toast({
      title: '❌ Could Not Access Clipboard - Manually copy the LLM chat',
    });
  }
}
