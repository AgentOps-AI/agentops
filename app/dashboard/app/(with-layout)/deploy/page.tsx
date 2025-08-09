'use client';
import { useHeaderContext } from '@/app/providers/header-provider';
import { Loading03Icon as Loader2 } from 'hugeicons-react';
import React, { useEffect, useState } from 'react';
import { useProjects as useProjectsQueryHook } from '@/hooks/queries/useProjects';
import { useOrgs as useOrgsQueryHook } from '@/hooks/queries/useOrgs';
import { useDeployments } from '@/hooks/queries/useProjects';
import { Button } from '@/components/ui/button';
import { SubscriptionBadge } from '@/components/ui/subscription-badge';
import { Separator } from '@/components/ui/separator';
import { getDerivedPermissions } from '@/types/IPermissions';
import { IProject } from '@/types/IProject';
import { IOrg } from '@/types/IOrg';
import { BookOpen, PlayCircle, ChevronDown, ChevronRight } from 'lucide-react';
import { useRouter, usePathname } from 'next/navigation';
import GithubConnectModal from './GithubConnectModal';
import { DeployPageSkeleton, LoadingSpinner } from './deploy-skeletons';
import AlphaWarningModal from './AlphaWarningModal';

export default function DeployPage() {
  const { setHeaderTitle, setHeaderContent } = useHeaderContext?.() || {};
  const {
    data: projects,
    isLoading: projectsLoading,
    error: projectsError,
  } = useProjectsQueryHook();
  const { data: orgsForDropdown, isLoading: orgsLoading, error: orgsError } = useOrgsQueryHook();
  const {
    data: deployments,
    isLoading: deploymentsLoading,
    error: deploymentsError,
  } = useDeployments();
  const deploymentsSet = new Set((deployments ?? []).map((p) => p.id));
  const [openProjectId, setOpenProjectId] = useState<string | null>(null);
  const [showMore, setShowMore] = useState<Record<string, boolean>>({});
  const [zoomingRocketId, setZoomingRocketId] = useState<string | null>(null);
  const [showAlphaWarning, setShowAlphaWarning] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  // ** wish.com feature flag **
  // Redirect if user is not in the required org
  useEffect(() => {
    if (orgsLoading) return;
    if (typeof window === 'undefined') return; //client only
    if (pathname === '/projects') return;
  }, [orgsForDropdown, orgsLoading, pathname, router]);

  // Check if user has seen alpha warning
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const hasSeenAlphaWarning = localStorage.getItem('deploy-alpha-warning-seen');
    if (!hasSeenAlphaWarning) {
      setShowAlphaWarning(true);
    }
  }, []);

  useEffect(() => {
    setHeaderTitle?.('Deploy');
    setHeaderContent?.(null);
  }, [setHeaderContent, setHeaderTitle]);

  const handleAlphaWarningClose = () => {
    setShowAlphaWarning(false);
    router.push('/projects');
  };

  const handleAlphaWarningContinue = () => {
    localStorage.setItem('deploy-alpha-warning-seen', 'true');
    setShowAlphaWarning(false);
  };

  // Group projects by org, similar to ProjectsList
  const projectsByOrg = (projects ?? []).reduce(
    (acc, project) => {
      const orgId = project.org.id;
      if (!acc[orgId]) {
        acc[orgId] = {
          org: project.org,
          projects: [],
        };
      }
      acc[orgId].projects.push(project);
      return acc;
    },
    {} as Record<string, { org: IOrg; projects: IProject[] }>,
  );
  (orgsForDropdown ?? []).forEach((org) => {
    if (!projectsByOrg[org.id]) {
      projectsByOrg[org.id] = {
        org: org,
        projects: [],
      };
    }
  });
  const sortedOrgEntries = Object.entries(projectsByOrg).sort(([, a], [, b]) => {
    const aPermissions = getDerivedPermissions(a.org);
    const bPermissions = getDerivedPermissions(b.org);
    if (aPermissions.tierName === 'pro' && bPermissions.tierName === 'free') return -1;
    if (aPermissions.tierName === 'free' && bPermissions.tierName === 'pro') return 1;
    return a.org.name.localeCompare(b.org.name);
  });

  // Show loading skeleton if either orgs or projects are loading
  if (orgsLoading || projectsLoading) {
    return (
      <>
        <style>{`
          @keyframes rocket-zoom-move {
            0% {
              opacity: 1;
              transform: translate(0, 0) scale(1);
            }
            80% {
              opacity: 1;
              transform: translate(220px, -220px) scale(1.5);
            }
            100% {
              opacity: 0;
              transform: translate(300px, -300px) scale(2);
            }
          }
          .rocket-zoom-animate {
            animation: rocket-zoom-move 0.7s cubic-bezier(0.4, 0.2, 0.2, 1) 1;
            pointer-events: none;
          }
          
          /* Dark mode specific animations if needed */
          .dark .rocket-zoom-animate {
            /* Could add dark-specific animation tweaks here if needed */
          }
        `}</style>
        <DeployPageSkeleton />
      </>
    );
  }

  return (
    <>
      <style>{`
        @keyframes rocket-zoom-move {
          0% {
            opacity: 1;
            transform: translate(0, 0) scale(1);
          }
          80% {
            opacity: 1;
            transform: translate(220px, -220px) scale(1.5);
          }
          100% {
            opacity: 0;
            transform: translate(300px, -300px) scale(2);
          }
        }
        .rocket-zoom-animate {
          animation: rocket-zoom-move 0.7s cubic-bezier(0.4, 0.2, 0.2, 1) 1;
          pointer-events: none;
        }
        
        /* Dark mode specific animations if needed */
        .dark .rocket-zoom-animate {
          /* Could add dark-specific animation tweaks here if needed */
        }
      `}</style>
      <div className="flex max-w-6xl flex-col gap-2 p-2">
        <div className="flex items-center gap-3 my-4">
          <h1 className="font-['Figtree'] text-[32px] font-bold text-gray-900 dark:text-white">
            Agent Hosting
          </h1>
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
            Alpha
          </span>
        </div>
        <p className="text-gray-700 dark:text-gray-300">Deploy your agent easily with AgentOps.</p>
        <div className="flex gap-4 my-4">
          <Button
            variant="outline"
            className="flex items-center gap-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            onClick={() => window.open('https://docs.agentops.ai/deployment', '_blank')}
          >
            <BookOpen className="h-4 w-4" />
            Documentation
          </Button>
          <Button
            variant="outline" 
            className="flex items-center gap-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            onClick={() => window.open('https://docs.agentops.ai/tutorials/deploy', '_blank')}
          >
            <PlayCircle className="h-4 w-4" />
            Tutorial
          </Button>
        </div>
        <div className="sm:align-center sm:flex sm:flex-col">
          {/* Show spinner for deployments loading */}
          {deploymentsLoading && <LoadingSpinner />}
          
          {/* Error states */}
          {projectsError && (
            <p className="text-[14px] text-red-500 dark:text-red-400">Error loading projects: {projectsError.message}</p>
          )}
          {orgsError && (
            <p className="text-[14px] text-red-500 dark:text-red-400">Error loading organizations: {orgsError.message}</p>
          )}
          
          {/* Main content */}
          {!projectsError && (
            <div className="space-y-8">
              {sortedOrgEntries.map(([orgId, { org, projects: orgProjects }]) => {
                const orgPermissions = getDerivedPermissions(org);
                const tierName = orgPermissions.tierName || 'current';
                const currentProjectCount = orgProjects.length;
                // Sort projects by trace_count descending
                const sortedProjects = [...orgProjects].sort((a, b) => b.trace_count - a.trace_count);
                const topProjects = sortedProjects.slice(0, 3);
                const moreProjects = sortedProjects.slice(3);
                return (
                  <div key={orgId}>
                    <div className="mb-4">
                      <div className="flex items-center gap-3">
                        <h3 className="text-[16px] font-medium text-gray-900 dark:text-white font-['Figtree']">
                          {org.name}
                        </h3>
                        <SubscriptionBadge
                          tier={tierName}
                          showUpgrade={false}
                          className="relative select-none"
                        />
                      </div>
                      <p className="mt-1 text-[14px] text-gray-600 dark:text-gray-400 font-['Figtree']">
                        {currentProjectCount} projects
                      </p>
                    </div>
                    <div className="mb-4 grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                      {topProjects.map((project) => {
                        const hasDeployment = deploymentsSet.has(project.id);
                        if (hasDeployment) {
                          return (
                            <div
                              key={project.id}
                              role="button"
                              tabIndex={0}
                              aria-label={`Go to deployment for ${project.name}`}
                              onClick={() => router.push(`/deploy/${project.id}`)}
                              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') router.push(`/deploy/${project.id}`); }}
                              className="relative flex flex-row items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 min-h-[72px] cursor-pointer transition-all duration-150 hover:shadow-lg hover:border-green-500 dark:hover:border-green-400 hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-green-500 dark:focus:ring-green-400 max-w-[420px]"
                            >
                              <div className="flex flex-col gap-0.5 w-full pr-4">
                                <h2 className="text-[16px] font-semibold text-gray-900 dark:text-white mb-0.5 truncate">{project.name}</h2>
                                <p className="text-[13px] text-gray-600 dark:text-gray-400">Traces: {project.trace_count}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="inline-block w-3 h-3 rounded-full bg-green-500 dark:bg-green-400 mr-1 border border-green-500 dark:border-green-400" aria-label="Running" />
                                <span className="text-[14px] font-medium text-green-600 dark:text-green-400 font-['Figtree']">Running</span>
                              </div>
                            </div>
                          );
                        } else {
                          return (
                            <div
                              key={project.id}
                              className="relative flex flex-row items-center justify-between rounded-xl border border-dashed border-gray-200 dark:border-gray-700 bg-white/40 dark:bg-gray-800/40 px-4 py-3 min-h-[72px] max-w-[420px]"
                            >
                              <div className="flex flex-col gap-0.5 opacity-60 pointer-events-none select-none w-full pr-4">
                                <h2 className="text-[16px] font-semibold text-gray-900 dark:text-white mb-0.5 truncate">{project.name}</h2>
                                <p className="text-[13px] text-gray-600 dark:text-gray-400">Traces: {project.trace_count}</p>
                              </div>
                              <GithubConnectModal
                                open={openProjectId === project.id}
                                onOpenChange={(open) => setOpenProjectId(open ? project.id : null)}
                                project={project}
                                org={org}
                                zoomingRocketId={zoomingRocketId}
                                setZoomingRocketId={setZoomingRocketId}
                              />
                            </div>
                          );
                        }
                      })}
                    </div>
                    {moreProjects.length > 0 && (
                      <>
                        <span
                          className="flex items-center gap-1 mt-2 text-[14px] italic text-gray-500 dark:text-gray-400 cursor-pointer select-none font-['Figtree'] ml-6 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                          onClick={() => setShowMore((prev) => ({ ...prev, [orgId]: !prev[orgId] }))}
                          role="button"
                          tabIndex={0}
                        >
                          more projects
                          {showMore[orgId] ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </span>
                        {showMore[orgId] && (
                          <div className="mt-4 ml-6 grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                            {moreProjects.map((project) => {
                              const hasDeployment = deploymentsSet.has(project.id);
                              if (hasDeployment) {
                                return (
                                  <div
                                    key={project.id}
                                    role="button"
                                    tabIndex={0}
                                    aria-label={`Go to deployment for ${project.name}`}
                                    onClick={() => router.push(`/deploy/${project.id}`)}
                                    onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') router.push(`/deploy/${project.id}`); }}
                                    className="relative flex flex-row items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 min-h-[72px] cursor-pointer transition-all duration-150 hover:shadow-lg hover:border-green-500 dark:hover:border-green-400 hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-green-500 dark:focus:ring-green-400 max-w-[420px]"
                                  >
                                    <div className="flex flex-col gap-0.5 w-full pr-4">
                                      <h2 className="text-[16px] font-semibold text-gray-900 dark:text-white mb-0.5 truncate">{project.name}</h2>
                                      <p className="text-[13px] text-gray-600 dark:text-gray-400">Traces: {project.trace_count}</p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <span className="inline-block w-3 h-3 rounded-full bg-green-500 dark:bg-green-400 mr-1 border border-green-500 dark:border-green-400" aria-label="Running" />
                                      <span className="text-[14px] font-medium text-green-600 dark:text-green-400 font-['Figtree']">Running</span>
                                    </div>
                                  </div>
                                );
                              } else {
                                return (
                                  <div
                                    key={project.id}
                                    className="relative flex flex-row items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-700 px-4 py-3 min-h-[72px] max-w-[420px]"
                                  >
                                    <div className="flex flex-col gap-0.5 opacity-60 pointer-events-none select-none w-full pr-4">
                                      <h2 className="text-[16px] font-semibold text-gray-900 dark:text-white mb-0.5 truncate">{project.name}</h2>
                                      <p className="text-[13px] text-gray-600 dark:text-gray-400">Traces: {project.trace_count}</p>
                                    </div>
                                    <GithubConnectModal
                                      open={openProjectId === project.id}
                                      onOpenChange={(open) => setOpenProjectId(open ? project.id : null)}
                                      project={project}
                                      org={org}
                                    />
                                  </div>
                                );
                              }
                            })}
                          </div>
                        )}
                      </>
                    )}
                    {sortedOrgEntries.findIndex(([id]) => id === orgId) < sortedOrgEntries.length - 1 && (
                      <Separator className="my-6 bg-gray-200 dark:bg-gray-700" />
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
      
      {/* Alpha Warning Modal */}
      <AlphaWarningModal
        isOpen={showAlphaWarning}
        onClose={handleAlphaWarningClose}
        onContinue={handleAlphaWarningContinue}
      />
    </>
  );
}