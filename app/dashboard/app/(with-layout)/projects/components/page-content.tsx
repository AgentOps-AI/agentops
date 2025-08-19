'use client';
import { useHeaderContext } from '@/app/providers/header-provider';
import { Loading03Icon as Loader2 } from 'hugeicons-react';
import React, { useEffect } from 'react';
import ProjectsList from './projects-list';
import { useProjects as useProjectsQueryHook } from '@/hooks/queries/useProjects';
import { ProjectCardSkeleton } from '@/components/ui/skeletons';
import { useOrgs as useOrgsQueryHook } from '@/hooks/queries/useOrgs';
import { ErrorDisplay } from '@/components/ui/error-display';

export const ProjectsPageContent = () => {
  const { setHeaderTitle, setHeaderContent } = useHeaderContext();
  const {
    data: projects,
    isLoading: projectsLoading,
    error: projectsError,
    refetch: refetchProjects,
  } = useProjectsQueryHook();
  const {
    data: orgsForDropdown,
    isLoading: orgsLoading,
    error: orgsError,
    refetch: refetchOrgs,
  } = useOrgsQueryHook();

  useEffect(() => {
    setHeaderTitle('Projects');
    setHeaderContent(null);
  }, [setHeaderContent, setHeaderTitle]);

  // Check if both have errors - likely the same root cause
  const hasBothErrors = projectsError && orgsError;

  return (
    <>
      <div className="sm:align-center sm:flex sm:flex-col">
        <div className="mb-4">{orgsLoading && <Loader2 className="h-4 w-4 animate-spin" />}</div>

        {projectsLoading && (
          <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <ProjectCardSkeleton key={index} />
            ))}
          </div>
        )}

        {/* Show combined error when both fail */}
        {hasBothErrors && (
          <ErrorDisplay
            error={projectsError}
            message="We're having trouble connecting to AgentOps. This might be due to a network issue or temporary service disruption."
            onRetry={() => {
              refetchProjects();
              refetchOrgs();
            }}
            errorContext={{
              component: 'ProjectsPageContent',
              action: 'load_data',
              hasMultipleErrors: true,
            }}
            className="mb-4"
          />
        )}

        {/* Show specific errors only when one fails */}
        {projectsError && !orgsError && (
          <ErrorDisplay
            error={projectsError}
            message="Unable to load your projects. Check your connection and try again."
            onRetry={refetchProjects}
            errorContext={{ component: 'ProjectsPageContent', action: 'load_projects' }}
            className="mb-4"
          />
        )}

        {orgsError && !projectsError && (
          <ErrorDisplay
            error={orgsError}
            message="Unable to load your organizations. This may affect project grouping."
            onRetry={refetchOrgs}
            errorContext={{ component: 'ProjectsPageContent', action: 'load_organizations' }}
            className="mb-4"
          />
        )}

        {!projectsLoading && !projectsError && (
          <ProjectsList projects={projects ?? []} orgs={orgsForDropdown ?? []} />
        )}
      </div>
    </>
  );
};
