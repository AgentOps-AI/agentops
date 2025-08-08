'use client';

import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  DatabaseIcon,
  GitBranchIcon,
  FileEditIcon,
  BookOpenIcon,
  CloudIcon,
  MessageSquareIcon,
  ZapIcon,
  X,
  ExternalLink,
  NetworkIcon
} from 'lucide-react';
import Link from 'next/link';
import Logo from '@/components/icons/Logo';
import { LangGraphIcon, AgnoIcon } from '@/components/icons';
import MCPLogo from '@/components/icons/MCPLogo';

interface PatchNote {
  icon: React.ReactNode;
  title: string;
  description: string;
  link?: {
    href: string;
    text: string;
  };
}

interface PatchNotesModalProps {
  version?: string;
  patchNotes?: PatchNote[];
  changelogUrl?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

const defaultPatchNotes: PatchNote[] = [
  {
    icon: <MCPLogo className="w-4 h-4" />,
    title: 'MCP (Model Context Protocol) Launch',
    description: 'Chat with your traces using the new MCP integration. Compatible with Cursor, Windsurf, Claude, and more.',
    link: {
      href: '/mcp',
      text: 'Learn more'
    }
  },
  {
    icon: <LangGraphIcon className="w-4 h-4" />,
    title: 'LangGraph Integration',
    description: 'Connect AgentOps workflows to LangGraph for richer automation & visualization',
    link: {
      href: 'https://docs.agentops.ai/v2/integrations/langgraph',
      text: 'View docs'
    }
  },
  {
    icon: <AgnoIcon className="w-4 h-4" />,
    title: 'Instrumentation & Agno UX Upgrades',
    description: 'Higher-accuracy metrics and a cleaner interface'
  },
  {
    icon: <NetworkIcon className="w-4 h-4 text-slate-600" />,
    title: 'New Graph View',
    description: 'Visualize agent traces as interactive execution graphs for better debugging and insights'
  },
  {
    icon: <CloudIcon className="w-4 h-4 text-slate-600" />,
    title: 'Public API Launched & Refined',
    description: 'Easier external integrations with greater stability',
    link: {
      href: 'https://docs.agentops.ai/v2/usage/public-api',
      text: 'API docs'
    }
  },
  {
    icon: <DatabaseIcon className="w-4 h-4 text-slate-600" />,
    title: 'Dynamic Trace Metadata',
    description: 'Edit and monitor traces on the fly in the Python SDK with `update_trace_metadata`'
  },
  {
    icon: <GitBranchIcon className="w-4 h-4 text-slate-600" />,
    title: 'Stronger Concurrency Handling',
    description: 'Smoother, more reliable parallel operations'
  },
  {
    icon: <FileEditIcon className="w-4 h-4 text-slate-600" />,
    title: 'Span Resource Attributes Capped',
    description: 'Leaner traces and faster processing'
  },
  {
    icon: <BookOpenIcon className="w-4 h-4 text-slate-600" />,
    title: 'Revamped Notebooks & Docs',
    description: 'Clearer examples, fixed links, and new session-management guides'
  },
  {
    icon: <MessageSquareIcon className="w-4 h-4 text-slate-600" />,
    title: 'Oversized-Chat Truncation',
    description: 'Lightning-fast loading of very long conversations'
  },
  {
    icon: <ZapIcon className="w-4 h-4 text-slate-600" />,
    title: 'General Performance Boosts',
    description: 'Quicker page loads plus auto-save protection'
  }
];

export function PatchNotesModal({
  version = '0.4.17',
  patchNotes = defaultPatchNotes,
  changelogUrl = 'https://agentops.ai/blog/v0.4.17',
  open,
  onOpenChange
}: PatchNotesModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const storageKey = `patch-notes-dismissed-${version}`;

  const controlledOpen = open !== undefined ? open : isOpen;
  const handleOpenChange = (newOpen: boolean) => {
    if (onOpenChange) {
      onOpenChange(newOpen);
    } else {
      setIsOpen(newOpen);
    }
  };

  useEffect(() => {
    // Only auto-open if not controlled
    if (open === undefined) {
      // Check if this version's patch notes have already been dismissed
      const isDismissed = localStorage.getItem(storageKey) === 'true';

      if (!isDismissed) {
        // Add a small delay to ensure the page has loaded
        const timer = setTimeout(() => {
          setIsOpen(true);
        }, 500);

        return () => clearTimeout(timer);
      }
    }
  }, [storageKey, open]);

  const handleDismiss = () => {
    localStorage.setItem(storageKey, 'true');
    handleOpenChange(false);
  };

  return (
    <Dialog open={controlledOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md p-0 max-h-[80vh] flex flex-col">
        <div className="p-6 pb-4 flex-1 min-h-0 flex flex-col">
          <DialogClose
            onClick={handleDismiss}
            className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-white transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-slate-950 focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-slate-100 data-[state=open]:text-slate-500 dark:ring-offset-slate-950 dark:focus:ring-slate-300 dark:data-[state=open]:bg-slate-800 dark:data-[state=open]:text-slate-400 z-10"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </DialogClose>

          <DialogHeader className="space-y-2 flex-shrink-0">
            <DialogTitle className="text-xl font-semibold text-center flex items-center justify-center gap-2">
              <Logo className="h-6 w-6" />
              <span>What&apos;s New in v{version}</span>
            </DialogTitle>
          </DialogHeader>

          <div className="mt-6 space-y-3 overflow-y-auto flex-1 pr-2 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-700">
            {patchNotes.map((note, index) => (
              <div key={index} className="flex gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {note.icon}
                </div>
                <div className="space-y-0.5">
                  <h3 className="font-medium text-sm text-slate-900 dark:text-slate-100">
                    {note.title}
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    {note.description}
                  </p>
                  {note.link && (
                    <Link
                      href={note.link.href}
                      className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 mt-1"
                      onClick={() => handleOpenChange(false)}
                      target={note.link.href.startsWith('http') ? '_blank' : undefined}
                      rel={note.link.href.startsWith('http') ? 'noopener noreferrer' : undefined}
                    >
                      {note.link.text}
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <DialogFooter className="px-6 py-4 bg-slate-50 dark:bg-slate-900 border-t flex-shrink-0">
          <div className="flex items-center justify-between w-full">
            <Link
              href={changelogUrl}
              className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              View Changelog
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
            <Button
              onClick={handleDismiss}
              className="px-6"
            >
              Continue
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}