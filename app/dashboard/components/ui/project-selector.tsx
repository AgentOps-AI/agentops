'use client';

import { useProject, ProjectContextType } from '@/app/providers/project-provider';
import { cn } from '@/lib/utils';
import { CheckmarkCircle01Icon as Check, Loading02Icon as LoaderCircle } from 'hugeicons-react';
import { memo, useEffect, useState } from 'react';
import { ArrowUp01Icon } from 'hugeicons-react';
import { ErrorDisplay } from './error-display';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from './dropdown-menu';
import { useProjects } from '@/hooks/queries/useProjects';
import { IProject } from '@/types/IProject';

interface GroupedProject {
  org_name: string;
  org_id: string;
  projects: IProject[];
}

interface ProjectSelectorComponentProps {
  containerClasses?: string;
  projects?: IProject[];
  isLoading?: boolean;
  selectedProject?: ProjectContextType['selectedProject'];
  setSelectedProject?: (project: IProject | null) => void;
  noShadow?: boolean;
}

function ProjectSelectorComponent({
  containerClasses,
  projects: projectsProp,
  isLoading: isLoadingProp,
  selectedProject: selectedProjectProp,
  setSelectedProject: setSelectedProjectProp,
  noShadow,
}: ProjectSelectorComponentProps) {
  const {
    data: projectsFromHook = [],
    isLoading: isLoadingFromHook,
    error: projectsError,
    refetch: refetchProjects,
  } = useProjects(undefined, { enabled: projectsProp === undefined });
  const projectCtx = useProject();

  const projects = projectsProp !== undefined ? projectsProp : projectsFromHook;
  const projectsLoading = isLoadingProp !== undefined ? isLoadingProp : isLoadingFromHook;
  const selectedProject =
    selectedProjectProp !== undefined ? selectedProjectProp : projectCtx.selectedProject;
  const setSelectedProject =
    setSelectedProjectProp !== undefined ? setSelectedProjectProp : projectCtx.setSelectedProject;

  const [isOpen, setIsOpen] = useState(false);
  const [groupedProjects, setGroupedProjects] = useState<GroupedProject[]>([]);

  useEffect(() => {
    if (!projectsLoading && projects.length > 0) {
      const projectsByOrg = projects.reduce((acc: Record<string, GroupedProject>, project) => {
        if (project && project.org) {
          const orgId = project.org.id;
          if (!acc[orgId]) {
            acc[orgId] = {
              org_id: orgId,
              org_name: project.org.name,
              projects: [],
            };
          }
          acc[orgId].projects.push(project);
        } else {
          console.warn('Project or project.org is missing for project:', project);
        }
        return acc;
      }, {});

      const newGroupedProjects = Object.values(projectsByOrg);

      setGroupedProjects(newGroupedProjects);
    }
  }, [projects, projectsLoading]);

  if (projectsError) {
    return (
      <ErrorDisplay
        error={projectsError}
        message="Unable to load projects for the dropdown"
        onRetry={refetchProjects}
        size="sm"
        errorContext={{ component: 'ProjectSelector', action: 'load_projects' }}
      />
    );
  }

  function setProject(value: string) {
    const project = projects.find((project) => project.id === value);
    if (project) {
      setSelectedProject(project);
    }
  }

  return (
    <>
      <DropdownMenu onOpenChange={(open) => setIsOpen(open)} modal={false}>
        <DropdownMenuTrigger
          className={cn(
            'shadow-md relative flex h-10 items-center justify-between gap-2 overflow-hidden rounded-md border border-[#DEE0F4] bg-[#F7F8FF] px-3 py-2 text-sm font-medium text-primary hover:bg-[#E1E3F2] focus:outline-none focus:ring-0 focus:ring-offset-0 active:ring-0 dark:border-gray-700 dark:bg-gray-800 dark:text-primary dark:hover:bg-gray-700 sm:min-w-[170px]',
            !noShadow && 'shadow-sm',
            containerClasses,
          )}
          disabled={projectsLoading}
          data-testid="project-selector"
        >
          <span
            style={{
              opacity: 0.3,
              backgroundImage: 'url(/image/grainy.png)',
              backgroundSize: '28px 28px',
            }}
            className="absolute inset-0 z-0 dark:hidden"
          />
          <div className="pointer-events-none relative z-10 truncate">
            {projectsLoading ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              (selectedProject?.name ?? 'Select Project')
            )}
          </div>
          <ArrowUp01Icon className={cn('relative z-10 h-4 w-4', isOpen ? '' : 'rotate-180 delay-75')} />
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-fit data-[state=closed]:fade-out-25" align="start">
          {groupedProjects.map((org) => (
            <DropdownMenuGroup key={org.org_id}>
              <DropdownMenuLabel className="opacity-50">{org.org_name}</DropdownMenuLabel>
              {org.projects.map((project: IProject) => (
                <DropdownMenuItem
                  key={project.id}
                  onSelect={() => {
                    setProject(project.id);
                  }}
                  className={cn(
                    project.id === selectedProject?.id && 'bg-[#E1E3F2] dark:bg-slate-700',
                  )}
                  data-testid={`project-selector-item-${project.id}`}
                >
                  {project.id === selectedProject?.id && (
                    <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
                      <Check className="h-4 w-4" />
                    </span>
                  )}
                  <div className="ml-6">{project.name}</div>
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </>
  );
}

const ProjectSelector = memo(ProjectSelectorComponent);

export default ProjectSelector;
