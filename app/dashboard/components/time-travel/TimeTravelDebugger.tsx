'use client';

import { GitBranchIcon as GitBranch, PlayIcon as Play } from 'hugeicons-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { HoverBorderGradient } from '@/components/ui/hover-border-gradient';
import Link from 'next/link';
import { ILlms } from '@/lib/interfaces';
import { BranchModal } from './BranchModal';
import { TimeTravelDebuggerModal } from './TimeTravelDebuggerModal';

type TimeTravelDebuggerProps = {
  llmEvents: ILlms[];
};

export default function TimeTravelDebugger({ llmEvents }: TimeTravelDebuggerProps) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <HoverBorderGradient
          containerClassName="rounded-full z-0"
          as="button"
          duration={0.2}
          className="flex items-center justify-center gap-2 space-x-2 bg-white text-[#3275F8] dark:bg-black dark:text-white"
        >
          <GitBranch color="#3275F8" size={24} />
          Time Travel
        </HoverBorderGradient>
      </DialogTrigger>

      <DialogContent className="h-5/6 w-4/5">
        <DialogHeader className="h-fit">
          <DialogTitle className="flex flex-row items-center justify-between gap-2">
            Rewrite History
            <Button className="m-0 mr-4 rounded-full" variant={'outline'}>
              <Link
                className="flex flex-row items-center gap-2"
                href="https://www.loom.com/embed/e8c2d47cc64446aba6589c2d58fb0d5e?sid=2afa6688-ecb6-4b8c-bd43-14ba7bd93815"
              >
                <Play className="inline-block" size={16} />
                Watch tutorial
              </Link>
            </Button>
          </DialogTitle>
          <DialogDescription className="text-md">
            Edit the completion of the selected LLM Event as you see fit.
            <br />
            The completions up to this point will be stored in a cache that you fetch with our CLI
            command. When you rerun your agent locally, the completions will be returned from the
            cache as opposed to your LLM. Everything after this point will go to your LLM.
            <br />
            <b className="semibold">
              Note: This feature is in alpha. Free for now but not forever :)
            </b>
          </DialogDescription>
        </DialogHeader>
        <TimeTravelDebuggerModal llmEvents={llmEvents} />
        <DialogFooter className="h-fit">
          <DialogClose asChild>
            {/* <BranchModal llmEvents={llmEvents} /> */}
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
