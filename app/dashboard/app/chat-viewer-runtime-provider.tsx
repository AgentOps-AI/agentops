import { completion, prompt, chatmlPrompt } from '@/lib/interfaces';
import {
  AppendMessage,
  AssistantRuntimeProvider,
  ThreadMessageLike,
  useExternalStoreRuntime,
} from '@assistant-ui/react';
import { ReactNode } from 'react';

export function ChatViewerRuntimeProvider({
  children,
  data,
  type,
}: Readonly<{
  children: ReactNode;
  data: completion[] | prompt[];
  type: string;
}>) {
  const convertMessage = (message: completion | prompt): ThreadMessageLike => {
    // Extract the content from the message based on its type
    let textContent = '';

    // Map arbitrary roles to valid assistant-ui roles
    const normalizedType = type === 'human' ? 'user' : type;

    if (normalizedType === 'user' || normalizedType === 'system' || normalizedType === 'tool') {
      // Handle prompt messages
      const promptMessage = message as prompt;
      if (promptMessage.type === 'chatml' && 'messages' in promptMessage) {
        const chatmlPromptMessage = promptMessage as chatmlPrompt;
        // Find the first message that matches the role (check both original and normalized)
        const roleMessage = chatmlPromptMessage.messages.find(m =>
          typeof m === 'object' && 'role' in m && (m.role === type || m.role === normalizedType)
        );

        if (roleMessage && typeof roleMessage.content === 'string') {
          textContent = roleMessage.content;
        }
      } else if (promptMessage.type === 'string' && 'string' in promptMessage) {
        textContent = promptMessage.string || '';
      } else {
        // Handle the message as a generic object to access potential properties
        const genericMessage = message as any;

        if ('user_query' in genericMessage) {
          // Special case for text prompts that are stored in user_query field
          textContent = genericMessage.user_query || '';
        } else if ('content' in genericMessage && typeof genericMessage.content === 'string') {
          // Direct content field (sometimes used in simple prompt structures)
          textContent = genericMessage.content;
        } else if ('role' in genericMessage && 'content' in genericMessage) {
          // Direct message object format - check both original and normalized roles
          if ((genericMessage.role === type || genericMessage.role === normalizedType) && typeof genericMessage.content === 'string') {
            textContent = genericMessage.content;
          }
        }
      }
    } else {
      // Handle completion messages
      const completionMessage = message as completion;
      if (completionMessage.type === 'chatml' && completionMessage.messages) {
        if (typeof completionMessage.messages.content === 'string') {
          textContent = completionMessage.messages.content;
        }
      } else if (completionMessage.type === 'string') {
        textContent = completionMessage.string || '';
      } else {
        // Handle the message as a generic object
        const genericMessage = message as any;

        if ('content' in genericMessage && typeof genericMessage.content === 'string') {
          // Direct content field
          textContent = genericMessage.content;
        } else if ('role' in genericMessage && 'content' in genericMessage) {
          // Handle direct message format
          if ((genericMessage.role === 'assistant' || genericMessage.role === type) && typeof genericMessage.content === 'string') {
            textContent = genericMessage.content;
          }
        }
      }
    }

    // Map roles to valid assistant-ui roles
    // "human" -> "user", system/tool -> "assistant", others remain as is
    let effectiveRole: 'user' | 'assistant';
    if (type === 'human' || type === 'user') {
      effectiveRole = 'user';
    } else if (type === 'system' || type === 'tool' || type === 'assistant') {
      effectiveRole = 'assistant';
    } else {
      // For any other arbitrary role, default to assistant
      effectiveRole = 'assistant';
    }

    return {
      role: effectiveRole,
      content: [
        { type: 'text', text: textContent }
      ],
    };
  };

  const onNew = async (message: AppendMessage) => {
    if (message.content[0]?.type !== 'text') throw new Error('Only text messages are supported');
  };

  const runtime = useExternalStoreRuntime({
    isRunning: false,
    messages: data,
    convertMessage,
    onNew,
  });

  return <AssistantRuntimeProvider runtime={runtime}>{children}</AssistantRuntimeProvider>;
}
