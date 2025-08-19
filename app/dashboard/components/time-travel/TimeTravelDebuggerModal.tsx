'use client';

import { Label } from '@/components/ui/label';
import {
  FormattedCompletion,
  FormattedPrompt,
} from '@/components/charts/chat-summary/llm-chat-viewer';
import { useState, useRef, useEffect } from 'react';
import { Tables } from '@/lib/types_db';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { useTheme } from 'next-themes';
import { JsonEditor, ThemeInput } from 'json-edit-react';
import { ILlms } from '@/lib/interfaces';

type TimeTravelDebuggerModalProps = {
  llmEvents: ILlms[];
};

export function TimeTravelDebuggerModal({ llmEvents }: TimeTravelDebuggerModalProps) {
  const [activeIndex, setActiveIndex] = useState<number>(llmEvents.length - 1);
  const [hasSelectedEvent, setHasSelectedEvent] = useState(true);
  const [activeLLMEvent, setActiveLLMEvent] = useState<Tables<'llms'>>(llmEvents[activeIndex]);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    setActiveLLMEvent(llmEvents[activeIndex]);
  }, [activeIndex]);

  const llmsContainerRef = useRef<HTMLDivElement>(null);
  const scrollToBottom = () => {
    llmsContainerRef?.current?.scrollIntoView(false);
  };

  useEffect(() => {
    scrollToBottom();
  }, [llmEvents]);

  return (
    <div className="flex h-full w-full justify-start overflow-auto">
      <ResizablePanelGroup direction="horizontal" className="flex h-full w-full gap-8">
        <ResizablePanel defaultSize={2}>
          <ScrollArea className="h-full">
            <div ref={llmsContainerRef} id="llms_container" className="flex flex-col gap-2 p-1">
              {llmEvents.map((llmEvent, index) => {
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                const formattedPrompt = FormattedPrompt({
                  prompts: [llmEvent.prompt],
                });
                 // eslint-disable-next-line @typescript-eslint/no-unused-vars
                const formattedCompletion = FormattedCompletion({
                  completion: llmEvent.completion,
                  truncationLength: 500,
                });
                return (
                  <button
                    key={index}
                    className={`mr-3 rounded-sm bg-slate-100 p-4 text-left hover:opacity-40 dark:bg-slate-900 ${index === activeIndex ? ' outline outline-slate-400' : ''}`}
                    onMouseDown={() => {
                      setHasSelectedEvent(!hasSelectedEvent);
                      setActiveIndex(index);
                    }}
                    onMouseMove={() => {
                      if (hasSelectedEvent) {
                        setActiveIndex(index);
                      }
                    }}
                  >
                    <Label className="text-md font-medium" htmlFor="prompt">
                      Prompt
                    </Label>
                    <div className="ml-5 mt-1 text-sm">{formattedPrompt}</div>
                    <Label className="text-md font-medium" htmlFor="completion">
                      Completion
                    </Label>
                    <div className="ml-5 mt-1 text-sm">{formattedCompletion}</div>
                  </button>
                );
              })}
            </div>
          </ScrollArea>
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={3}>
          <ScrollArea className="h-full">
            <div id="editing_container" className="mr-3 flex flex-col gap-4">
              <div className="flex flex-col gap-3">
                <div>
                  <Label className="text-md font-medium" htmlFor="prompt">
                    Prompt
                  </Label>
                </div>
                <div>
                  {FormattedPrompt({
                    prompts: [llmEvents[activeIndex].prompt],
                  })}
                </div>
              </div>
              <div>
                <Label className="text-md font-medium" htmlFor="completion">
                  Completion
                </Label>
                <JsonEditor
                  data={JSON.parse(activeLLMEvent.returns ?? '{}')}
                  onUpdate={({ newData }) => {
                    activeLLMEvent.returns = JSON.stringify(newData);
                  }}
                  minWidth="100%"
                  indent={2}
                  theme={(resolvedTheme === 'dark' ? 'githubDark' : 'githubLight') as ThemeInput}
                  restrictEdit={({ path, key }) =>
                    path[0] !== 'choices' &&
                    key !== 'prompt_tokens' &&
                    key !== 'completion_tokens' &&
                    key !== 'total_tokens'
                  }
                  restrictDelete={({ path }) => !(path.length === 2 && path[0] === 'choices')}
                  restrictAdd={({ key }) => key !== 'choices'}
                  restrictTypeSelection={({ path }) =>
                    !(path.length === 2 && path[0] === 'choices')
                  }
                />
              </div>
            </div>
          </ScrollArea>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
