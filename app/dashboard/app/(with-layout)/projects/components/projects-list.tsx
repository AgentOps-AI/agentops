'use client';

import ProjectCard from './project-card';
import { useState } from 'react';
import { Card } from '@/components/ui/card';

import { ApiKeyModal } from './api-key-modal';
import { IProject } from '@/types/IProject';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createProjectAPI } from '@/lib/api/projects';
import { projectsQueryKey } from '@/hooks/queries/useProjects';
import { toast } from '@/components/ui/use-toast';
import { IOrg } from '@/types/IOrg';


import { getDerivedPermissions } from '@/types/IPermissions';
import { Separator } from '@/components/ui/separator';
import { PremiumUpsellBanner } from '@/components/ui/premium-upsell-banner';
import { cn } from '@/lib/utils';
import { ProjectDetails } from '@/components/ui/create-project-card';
import { AddCircleIcon as PlusCircle, LockPasswordIcon } from 'hugeicons-react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { SubscriptionBadge } from '@/components/ui/subscription-badge';

interface ProjectErrorProps {
  projectName?: string;
  selectedOrgId?: string;
}

interface ProjectsListProps {
  projects: IProject[];
  orgs: IOrg[];
}

export default function ProjectsList({ projects, orgs }: ProjectsListProps) {
  const queryClient = useQueryClient();
  const [projectName, setProjectName] = useState('');


  const [apiModal, setApiModal] = useState(false);
  const [newlyCreatedProject, setNewlyCreatedProject] = useState<IProject | null>(null);

  const [errors, setErrors] = useState<ProjectErrorProps>({ projectName: '', selectedOrgId: '' });
  const [createProjectOrgId, setCreateProjectOrgId] = useState<string | null>(null);

  const createProjectMutation = useMutation({
    mutationFn: createProjectAPI,
    onSuccess: (createdProject) => {
      queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      setNewlyCreatedProject(createdProject);
      setApiModal(true);
      if (typeof window !== 'undefined') {
        navigator.clipboard
          .writeText(createdProject.api_key)
          .then(() =>
            toast({ title: 'API Key Copied to Clipboard', description: createdProject.api_key }),
          )
          .catch(() =>
            toast({ title: '❌ Manually copy the API Key:', description: createdProject.api_key }),
          );
      }
    },
    onError: (error) => {
      console.error('Create project error:', error);
      toast({ title: '❌ Failed to Create Project', description: error.message });
      setErrors({ ...errors });
    },
  });











  const projectsByOrg = projects.reduce(
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

  // Ensure all orgs are included, even if they have no projects
  // since you can technically delete everything if you felt like it
  orgs.forEach((org) => {
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

  const getPlanDisplayName = (tierName: string) => {
    switch (tierName) {
      case 'free':
        return 'Hobby Plan';
      case 'pro':
        return 'Pro';
      case 'enterprise':
        return 'Enterprise';
      default:
        return 'Hobby Plan';
    }
  };

  const canCreateProjectsInOrg = (org: IOrg) => {
    return org.current_user_role === 'admin' || org.current_user_role === 'owner';
  };

  return (
    <div className="space-y-8">
      {sortedOrgEntries.map(([orgId, { org, projects: orgProjects }]) => {
        const orgPermissions = getDerivedPermissions(org);
        const maxAllowedProjects = orgPermissions.projects.maxAllowed;
        const tierName = orgPermissions.tierName || 'current';
        const currentProjectCount = orgProjects.length;
        const canCreateProjects = canCreateProjectsInOrg(org);

        const isOverLimit =
          typeof maxAllowedProjects === 'number' && currentProjectCount > maxAllowedProjects;

        const isAtLimit =
          typeof maxAllowedProjects === 'number' && currentProjectCount >= maxAllowedProjects;

        return (
          <div key={orgId}>
            <div className="mb-4">
              <div className="flex items-center gap-3">
                <h3 className="text-base font-medium text-primary">{org.name}</h3>
                <SubscriptionBadge
                  tier={tierName}
                  showUpgrade={false}
                  className="relative select-none"
                />
              </div>
              {tierName === 'pro' || tierName === 'enterprise' ? (
                <p className="mt-1 text-sm text-secondary dark:text-[#A3A8C9]">
                  {currentProjectCount} projects
                </p>
              ) : (
                typeof maxAllowedProjects === 'number' && (
                  <div className="mt-1 flex items-center gap-2">
                    <p className="text-sm text-secondary dark:text-[#A3A8C9]">
                      {currentProjectCount} / {maxAllowedProjects} projects used
                    </p>
                    {isAtLimit && (
                      <LockPasswordIcon
                        className="ml-1 h-4 w-4 text-gray-500"
                        aria-label="locked"
                      />
                    )}
                  </div>
                )
              )}
            </div>
            {isOverLimit && (
              <PremiumUpsellBanner
                title={`Project limit exceeded for ${org.name}`}
                messages={[
                  `Your ${getPlanDisplayName(tierName)} plan for ${org.name} allows for ${maxAllowedProjects} project(s). You currently have ${currentProjectCount}.`,
                  'To view all projects or create new ones, please upgrade your plan.',
                ]}
              />
            )}
            <div className="mb-4 grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
              {orgProjects.map((project, index) => {
                const isProjectOverLimit =
                  typeof maxAllowedProjects === 'number' && index >= maxAllowedProjects;

                return (
                  <ProjectCard
                    key={project.id}
                    project={project}
                    orgName={org.name ?? 'Unknown Org'}
                    orgs={orgs as IOrg[]}
                    isOverLimit={isProjectOverLimit}
                  />
                );
              })}

              {!isAtLimit && canCreateProjects && (
                <Card
                  className={cn(
                    'relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-gray-50/50 p-5 transition-all hover:border-blue-400 hover:bg-blue-50/30 hover:shadow-lg dark:border-gray-700 dark:bg-gray-900/50 dark:hover:border-blue-600 dark:hover:bg-blue-950/30',
                  )}
                  onClick={() => {
                    setCreateProjectOrgId(orgId);
                    setProjectName('');
                    setErrors({});
                  }}
                >
                  <PlusCircle className="mb-2 h-12 w-12 text-gray-400 dark:text-gray-600" />
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    New Project
                  </span>
                </Card>
              )}
            </div>
            {sortedOrgEntries.findIndex(([id]) => id === orgId) < sortedOrgEntries.length - 1 && (
              <Separator className="my-6" />
            )}
          </div>
        );
      })}

      {/* Onboarding dialog removed - no longer needed */}

      {/* API key modal after project creation */}
      {newlyCreatedProject && (
        <ApiKeyModal open={apiModal} onOpenChange={setApiModal} project={newlyCreatedProject} />
      )}

      {/* Create project dialog */}
      {/* Tutorial Video */}
      <div className="mt-6 rounded-xl border border-gray-200 bg-gradient-to-br from-blue-50/50 to-purple-50/50 p-4 dark:border-gray-700 dark:from-blue-950/20 dark:to-purple-950/20 lg:max-w-3xl">
        <div className="mb-3">
          <h3 className="text-base font-semibold text-primary dark:text-white">
            Getting Started with AgentOps
          </h3>
          <p className="mt-0.5 text-xs text-secondary dark:text-[#A3A8C9]">
            Watch this quick tutorial to learn how to integrate AgentOps into your project
          </p>
        </div>
        <div className="aspect-video w-full overflow-hidden rounded-lg shadow-md">
          <iframe
            className="h-full w-full"
            src="https://www.youtube.com/embed/EU_A3_ux09s"
            title="AgentOps Tutorial"
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        </div>
      </div>
      {createProjectOrgId && (
        <Dialog
          open={!!createProjectOrgId}
          onOpenChange={(open) => {
            if (!open) {
              setCreateProjectOrgId(null);
              setProjectName('');
              setErrors({});
            }
          }}
        >
          <DialogContent className="w-3/4 rounded-xl sm:w-[506px]">
            <ProjectDetails
              orgs={orgs}
              project_name={projectName}
              org_name={orgs.find((o) => o.id === createProjectOrgId)?.name}
              isEdit={false}
              handleModalClose={() => {
                setCreateProjectOrgId(null);
              }}
              lockedOrgId={createProjectOrgId}
            />
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
