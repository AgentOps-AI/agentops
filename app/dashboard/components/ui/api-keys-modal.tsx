'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { BackgroundImageOverlay } from '@/components/ui/background-image-overlay';
import { useOrgs } from '@/hooks/queries/useOrgs';
import { useProjects } from '@/hooks/queries/useProjects';
import { ApiKeyBox } from '@/components/ui/api-key-box';
import { Copy01Icon as Copy } from 'hugeicons-react';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from '@/components/ui/use-toast';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { SubscriptionBadge } from '@/components/ui/subscription-badge';
import { cn } from '@/lib/utils';

interface ApiKeysModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function ProjectsList({ orgId, premStatus }: { orgId: string; premStatus: string | null }) {
  const { data: projects, isLoading } = useProjects(orgId);

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  if (!projects || projects.length === 0) {
    return <p className="text-sm text-muted-foreground">No projects found</p>;
  }

  const copyApiKey = (apiKey: string, projectName: string) => {
    if (typeof window !== 'undefined') {
      navigator.clipboard
        .writeText(apiKey)
        .then(() =>
          toast({
            title: 'API Key Copied',
            description: `Copied API key for ${projectName}`,
          }),
        )
        .catch(() => toast({ title: '❌ Manually copy API Key:', description: apiKey }));
    }
  };

  const isPro = premStatus === 'pro';

  return (
    <div className="space-y-3">
      {projects.map((project, index) => {
        const shouldBlur = !isPro && projects.length > 1 && index > 0;
        return (
          <div
            key={project.id}
            className={cn(
              'flex items-center justify-between rounded-lg border bg-slate-50 p-3 dark:bg-slate-800/50',
              shouldBlur && 'pointer-events-none opacity-50',
            )}
          >
            <div className="font-medium">{project.name}</div>
            <div className="flex items-center gap-1">
              <ApiKeyBox apiKey={project.api_key} />
              <TooltipProvider>
                <Tooltip delayDuration={0}>
                  <TooltipTrigger asChild>
                    <button
                      className="flex h-8 w-8 items-center justify-center rounded hover:bg-slate-200 dark:hover:bg-slate-700"
                      onClick={() => copyApiKey(project.api_key, project.name)}
                    >
                      <Copy className="h-4 w-4 cursor-pointer hover:text-blue-600" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>Copy API Key</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ApiKeysModal({ open, onOpenChange }: ApiKeysModalProps) {
  const { data: orgs, isLoading: orgsLoading } = useOrgs();

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent
        className="max-h-[80vh] w-[90vw] max-w-2xl overflow-hidden rounded-2xl border border-white bg-[#F7F8FF] dark:border-slate-700 dark:bg-slate-900 sm:rounded-2xl"
        overlayClassName="bg-white/40 backdrop-blur-md dark:bg-black/40"
      >
        <BackgroundImageOverlay />
        <div className="relative">
          <DialogHeader className="mb-6">
            <DialogTitle className="text-left text-2xl font-medium text-primary">
              API Keys
            </DialogTitle>
            <DialogDescription className="text-left font-medium text-secondary dark:text-slate-300">
              Access all your API keys across organizations and projects
            </DialogDescription>
          </DialogHeader>

          <div className="max-h-[60vh] space-y-6 overflow-y-auto pr-2">
            {orgsLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-32 w-full" />
              </div>
            ) : !orgs || orgs.length === 0 ? (
              <p className="text-center text-muted-foreground">No organizations found</p>
            ) : (
              orgs.map((org) => (
                <div key={org.id} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold">{org.name}</h3>
                    <SubscriptionBadge tier={org.prem_status} showUpgrade={false} />
                  </div>
                  <ProjectsList orgId={org.id} premStatus={org.prem_status} />
                </div>
              ))
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
