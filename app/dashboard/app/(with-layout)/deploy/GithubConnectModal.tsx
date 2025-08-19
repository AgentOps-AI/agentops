import React, { useState } from 'react';
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogFooter, DialogTitle, DialogDescription, DialogClose } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Rocket } from 'lucide-react';
import { IProject } from '@/types/IProject';
import { IOrg } from '@/types/IOrg';
import { getDerivedPermissions } from '@/types/IPermissions';

interface GithubConnectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project: IProject;
  org: IOrg;
  zoomingRocketId?: string | null;
  setZoomingRocketId?: (id: string | null) => void;
}

const GithubConnectModal: React.FC<GithubConnectModalProps> = ({
  open,
  onOpenChange,
  project,
  org,
  zoomingRocketId,
  setZoomingRocketId,
}) => {
  const [isRedirecting, setIsRedirecting] = useState(false);
  const tier = getDerivedPermissions(org).tierName;

  const handleConnectGithub = () => {
    setIsRedirecting(true)
    // Store projectId in localStorage
    if (project?.id) {
      localStorage.setItem('github_connect_project_id', project.id);
    }
    const clientId = process.env.NEXT_PUBLIC_GITHUB_OAUTH_CLIENT_ID;
    const redirectUri = encodeURIComponent(process.env.NEXT_PUBLIC_GITHUB_OAUTH_CALLBACK_URL || 'https://app.agentops.ai/deploy/github-callback');
    const scope = 'repo'; // Full control of private repositories
    const state = Math.random().toString(36).substring(2);

    window.location.href =
      `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}&state=${state}`
  };

  if (tier === 'free') {
    // Hobby org: show upgrade modal
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogTrigger asChild>
          <Button
            variant="secondary"
            className="group flex flex-col items-center justify-center py-2 h-14 w-20 ml-2 px-0 py-0 bg-gray-100/40 hover:bg-gray-50 text-[14px] font-['Figtree'] text-gray-700 border border-[rgba(222,224,244,1)] hover:shadow-sm focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-blue-300 transition-all"
            style={{ fontFamily: 'Figtree, sans-serif', opacity: 1 }}
            onClick={e => {
              e.stopPropagation();
              setZoomingRocketId?.(project.id);
            }}
            disabled={zoomingRocketId === project.id}
          >
            <span style={{ display: 'inline-block', position: 'relative', width: 24, height: 24 }}>
              {zoomingRocketId === project.id ? (
                <Rocket
                  className={`h-6 w-6 rocket-move rainbow-gradient rocket-zoom-animate`}
                  style={{ position: 'absolute', left: 0, top: 0 }}
                  onAnimationEnd={() => setZoomingRocketId?.(null)}
                />
              ) : (
                <Rocket className="h-6 w-6 rocket-move rainbow-gradient" />
              )}
            </span>
            Deploy
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-['Figtree'] text-[16px] text-[rgba(20,27,52,1)]">Agent hosting is only available to AgentOps Pro orgs!</DialogTitle>
            <DialogDescription className="font-['Figtree'] text-[14px] text-[rgba(20,27,52,0.74)]">
              Upgrade your organization to unlock agent hosting and deployment features.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" className="font-['Figtree'] text-[14px]">Cancel</Button>
            </DialogClose>
            <DialogClose asChild>
              <Button variant="default" className="font-['Figtree'] text-[14px]" onClick={() => window.location.href = '/settings/billing'}>Upgrade</Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  // Pro/Enterprise org: show normal connect modal
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button
          variant="secondary"
          className="group flex flex-col items-center justify-center py-2 h-14 w-20 ml-2 px-0 py-0 bg-gray-100/40 hover:bg-gray-50 text-[14px] font-['Figtree'] text-gray-700 border border-[rgba(222,224,244,1)] hover:shadow-sm focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-blue-300 transition-all"
          style={{ fontFamily: 'Figtree, sans-serif', opacity: 1 }}
          onClick={e => {
            e.stopPropagation();
            setZoomingRocketId?.(project.id);
          }}
          disabled={zoomingRocketId === project.id}
        >
          <span style={{ display: 'inline-block', position: 'relative', width: 24, height: 24 }}>
            {zoomingRocketId === project.id ? (
              <Rocket
                className={`h-6 w-6 rocket-move rainbow-gradient rocket-zoom-animate`}
                style={{ position: 'absolute', left: 0, top: 0 }}
                onAnimationEnd={() => setZoomingRocketId?.(null)}
              />
            ) : (
              <Rocket className="h-6 w-6 rocket-move rainbow-gradient" />
            )}
          </span>
          Deploy
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="font-['Figtree'] text-[16px] text-[rgba(20,27,52,1)]">Connect your GitHub repo</DialogTitle>
          <DialogDescription className="font-['Figtree'] text-[14px] text-[rgba(20,27,52,0.74)]">
            Would you like to connect your GitHub repository to deploy <b>{project.name}</b>?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" className="font-['Figtree'] text-[14px]">Cancel</Button>
          </DialogClose>
          <Button
            variant="default"
            className="font-['Figtree'] text-[14px]"
            onClick={handleConnectGithub}
            disabled={isRedirecting}
          >
            {isRedirecting ? 'Redirecting...' : 'Connect GitHub'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default GithubConnectModal; 