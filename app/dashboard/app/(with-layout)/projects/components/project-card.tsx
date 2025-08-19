'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { useProject } from '@/app/providers/project-provider';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { MoreHorizontalIcon as EllipsisIcon } from 'hugeicons-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Separator } from '@/components/ui/separator';
import { MenuItemsProps } from '@/types/common.types';
import { Key01Icon, PencilEdit01Icon as PencilEditIcon } from 'hugeicons-react';
import { Delete02Icon as TrashBinIcon } from 'hugeicons-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Copy01Icon as DuplicateIcon } from 'hugeicons-react';
import { BackgroundImageOverlay } from '@/components/ui/background-image-overlay';
import { ProjectDetails } from '@/components/ui/create-project-card';
import { Container } from '@/components/ui/container';
import { cn } from '@/lib/utils';
import { VisuallyHidden } from '@radix-ui/react-visually-hidden';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteProjectAPI, createProjectAPI } from '@/lib/api/projects';
import { projectsQueryKey } from '@/hooks/queries/useProjects';
import { toast } from '@/components/ui/use-toast';
import { Alert01Icon as AlertIcon } from 'hugeicons-react';
import { IProject } from '@/types/IProject';
import { IOrg } from '@/types/IOrg';
import { ApiKeyBox } from '@/components/ui/api-key-box';
import { Copy01Icon as Copy, AddCircleIcon as PlusCircle } from 'hugeicons-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

type ProjectMenuLabel = 'Rename' | 'Duplicate' | 'View API Key' | 'Remove';

const dialogContentStyles = 'w-3/4 sm:w-[506px] rounded-xl';

const menuIconStyles = 'mr-2 h-5 w-5';

const ProjectCard = ({
  project,
  orgName,
  orgs,
  cardStyles,
  disableDropdown = false,
  isOverLimit = false,
}: {
  project: IProject;
  orgName: string;
  orgs: IOrg[];
  cardStyles?: string;
  disableDropdown?: boolean;
  isOverLimit?: boolean;
}) => {
  const { selectedProject, setSelectedProject } = useProject();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [openDialog, setOpenDialog] = useState<ProjectMenuLabel>();
  const hasTraces = !!project.trace_count;

  const deleteMutation = useMutation({
    mutationFn: deleteProjectAPI,
    onMutate: async (variables) => {
      // Cancel any outgoing refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: projectsQueryKey });

      // Snapshot the previous value
      const previousProjects = queryClient.getQueryData<IProject[]>(projectsQueryKey);

      // Optimistically update to the new value
      queryClient.setQueryData<IProject[]>(projectsQueryKey, (old) => {
        if (!old) return [];
        return old.filter((project) => project.id !== variables.projectId);
      });

      // Return a context object with the snapshotted value
      return { previousProjects };
    },
    onError: (error, variables, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      if (context?.previousProjects) {
        queryClient.setQueryData(projectsQueryKey, context.previousProjects);
      }
      console.error('Delete project error:', error);
      toast({ title: `❌ Failed to delete ${project.name}: ${error.message}` });
    },
    onSuccess: (data, variables) => {
      if (data.success) {
        if (selectedProject?.id === variables.projectId) {
          setSelectedProject(null);
        }
        toast({
          icon: <AlertIcon className="h-[24px] w-[24px] stroke-[#E65A7E] dark:stroke-[#E65A7E]" />,
          title: 'Project Deleted',
          description: `Your project ${project.name} has been deleted`,
        });
      } else {
        // Revert the optimistic update if the server indicates failure
        queryClient.invalidateQueries({ queryKey: projectsQueryKey });
        toast({ title: `❌ Failed to delete ${project.name}: ${data.message || 'Unknown error'}` });
      }
    },
    onSettled: () => {
      // Always refetch after error or success to ensure consistency
      queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      closeDialog();
    },
  });

  const createMutation = useMutation({
    mutationFn: createProjectAPI,
    onSuccess: (newProject) => {
      queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      toast({ title: 'Project Duplicated', description: `Created ${newProject.name}` });
    },
    onError: (error) => {
      console.error('Duplicate project error:', error);
      toast({ title: '❌ Failed to Duplicate Project', description: error.message });
    },
  });

  const menuItemsPrimary: MenuItemsProps<ProjectMenuLabel>[] = [
    {
      icon: <PencilEditIcon className={menuIconStyles} />,
      label: 'Rename',
    },
    {
      icon: <DuplicateIcon className={menuIconStyles} />,
      label: 'Duplicate',
    },
    {
      icon: <Key01Icon className={menuIconStyles} />,
      label: 'View API Key',
    },
  ];

  const menuItemsSecondary: MenuItemsProps<ProjectMenuLabel>[] = [
    {
      icon: <TrashBinIcon className={menuIconStyles} />,
      label: 'Remove',
    },
  ];

  function duplicateProject(item: IProject) {
    if (item === null) {
      return;
    }
    const newName = `${item?.name} - copy`;
    createMutation.mutate({ org_id: item.org_id, name: newName });
  }

  const closeDialog = () => {
    setOpenDialog(undefined);
  };

  const handleMenuItemClick = (label: ProjectMenuLabel) => {
    if (label === 'Duplicate') {
      if (isOverLimit) {
        toast({
          title: 'Upgrade Required',
          description:
            'You have reached the project limit for your current plan. Please upgrade to duplicate projects.',
          variant: 'destructive',
        });
        return;
      }
      duplicateProject(project);
      return;
    }
    setOpenDialog(label);
  };

  const cardDisabledStyles = isOverLimit ? 'filter blur-sm grayscale opacity-70' : '';

  return (
    <>
      <Card
        className={cn(
          'relative flex cursor-pointer flex-col justify-between rounded-xl border-[1px] border-[#DEE0F4] bg-[#F7F8FF] p-5 hover:border-white hover:shadow-lg',
          !hasTraces && !isOverLimit && 'animate-pulse-subtle border-blue-300 shadow-glow-blue',
          cardStyles,
        )}
        onClick={(e) => {
          if (isOverLimit) {
            e.stopPropagation();
            return;
          }
          setSelectedProject(project);
          router.push(hasTraces ? '/overview' : '/get-started');
        }}
        key={project.id}
        data-testid={`project-card-${project.name}`}
      >
        {!hasTraces && !isOverLimit && (
          <div className="absolute -top-2.5 left-0 right-0 mx-auto w-fit rounded-full bg-blue-500 px-3 py-0.5 text-center text-xs font-semibold text-white shadow-md">
            New Project
          </div>
        )}
        <BackgroundImageOverlay />
        <div
          className={cn('relative z-[5]', isOverLimit && 'pointer-events-none', cardDisabledStyles)}
        >
          <div className="relative mb-1 flex items-center justify-between">
            <h2
              className={cn(
                'text-lg font-semibold text-primary dark:text-white',
                isOverLimit && 'opacity-50',
              )}
            >
              {project?.name || 'All Projects'}
            </h2>
            {!disableDropdown && !isOverLimit && (
              <div className="flex items-center space-x-1">
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <Button
                      className="-mr-2 -mt-2 rounded-lg px-2 py-1 hover:bg-[#E1E3F2]"
                      variant="ghost"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMenuItemClick('View API Key');
                      }}
                      aria-label="View API Key"
                    >
                      <Key01Icon className="h-5 w-5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">View API Key</TooltipContent>
                </Tooltip>
                <DropdownMenu modal={false}>
                  <DropdownMenuTrigger asChild>
                    <Button
                      className="-mr-2 -mt-2 rounded-lg px-2 py-1 hover:bg-[#E1E3F2]"
                      variant="ghost"
                      onClick={(e) => {
                        e.stopPropagation();
                      }}
                      aria-label="More options"
                    >
                      <EllipsisIcon className="cursor-pointer h-5 w-5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    className="z-10 w-40 rounded-xl p-2 opacity-90 dark:bg-background sm:mr-24"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {menuItemsPrimary
                      .filter((item) => item.label !== 'View API Key') // Exclude View API Key
                      .map(({ icon, label }, i) => {
                        if (label === 'Duplicate') {
                          return (
                            <React.Fragment key={label + i}>
                              {/* // TODO: Implement Duplicate Project functionality */}
                              {/*
                              <DropdownMenuItem onClick={() => handleMenuItemClick(label)}>
                                {icon}
                                <span className="text-secondary dark:text-white">{label}</span>
                              </DropdownMenuItem>
                              */}
                            </React.Fragment>
                          );
                        }
                        return (
                          <DropdownMenuItem key={label + i} onClick={() => handleMenuItemClick(label)}>
                            {icon}
                            <span className="text-secondary dark:text-white">{label}</span>
                          </DropdownMenuItem>
                        );
                      })}
                    <Separator className="my-1" />
                    {menuItemsSecondary.map(({ icon, label }, i) => (
                      <DropdownMenuItem key={label + i} onClick={() => handleMenuItemClick(label)}>
                        {icon}
                        <span className="text-secondary dark:text-white">{label}</span>
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}
          </div>

          <div className="mb-4 flex flex-col">
            <p
              className={cn(
                'text-xs font-medium text-gray-500 dark:text-gray-400',
                isOverLimit && 'opacity-50',
              )}
            >
              Organization: <span className="text-secondary dark:text-white">{orgName}</span>
            </p>
          </div>

          <div
            className={cn('mt-auto flex items-center justify-between', isOverLimit && 'opacity-50')}
          >
            <p className="text-xs font-medium text-secondary dark:text-white">
              <span className="font-semibold">{(project.trace_count ?? 0).toLocaleString()}</span>{' '}
              {project.trace_count === 1 ? 'Trace' : 'Traces'}
            </p>

            {!hasTraces && !isOverLimit && (
              <Tooltip delayDuration={150}>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1 rounded-md bg-blue-500 px-3 py-1.5 text-sm font-medium text-white shadow-sm">
                    <PlusCircle className="h-4 w-4" />
                    <span>Start</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom">Begin using this project</TooltipContent>
              </Tooltip>
            )}
          </div>
        </div>
      </Card>
      <Dialog onOpenChange={closeDialog} open={openDialog === 'Rename'}>
        <DialogContent className={dialogContentStyles}>
          <VisuallyHidden>
            <DialogTitle>Project Details</DialogTitle>
          </VisuallyHidden>
          <ProjectDetails
            orgs={orgs}
            project_id={project?.id}
            project_name={project?.name}
            org_name={orgName}
            isEdit
            handleModalClose={closeDialog}
          />
        </DialogContent>
      </Dialog>
      <Dialog onOpenChange={closeDialog} open={openDialog === 'View API Key'}>
        <DialogContent className={dialogContentStyles}>
          <DialogHeader>
            <DialogTitle className="text-left text-lg font-medium text-primary">
              API Key
            </DialogTitle>
            <DialogDescription className="text-left font-medium text-secondary dark:text-white">
              Here is the API key for <span className="text-primary">{project?.name}</span>
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-3 py-2">
            {project?.api_key && <ApiKeyBox apiKey={project.api_key} />}
            {project?.api_key && (
              <Tooltip delayDuration={0}>
                <TooltipTrigger asChild>
                  <div className="flex w-5 items-center">
                    <Copy
                      className="w-5 cursor-pointer hover:text-blue-600"
                      onClick={() => {
                        navigator.clipboard
                          ?.writeText(project.api_key)
                          .then(() => {
                            toast({
                              title: 'API Key Copied to Clipboard',
                              description: `Copied API key for ${project.name}`,
                            });
                          })
                          .catch(() => {
                            toast({
                              title: '❌ Could Not Access Clipboard',
                              description: 'Please copy the key manually.',
                            });
                          });
                      }}
                    />
                  </div>
                </TooltipTrigger>
                <TooltipContent>Copy API Key</TooltipContent>
              </Tooltip>
            )}
          </div>
          <DialogFooter className="flex flex-row text-sm text-secondary dark:text-white sm:justify-start">
            View all API Keys{' '}
            <span
              className="cursor-pointer pl-1 text-primary underline"
              onClick={() => router.push('settings/projects')}
            >
              Here
            </span>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog onOpenChange={closeDialog} open={openDialog === 'Remove'}>
        <DialogContent className={dialogContentStyles}>
          <DialogHeader>
            <DialogTitle className="text-left text-lg font-medium text-primary">
              Delete Project
            </DialogTitle>
            <DialogDescription className="text-left font-medium text-secondary">
              {`Are you sure you want to delete this project? This action can't be undone so
              choose wisely.`}
            </DialogDescription>
          </DialogHeader>
          <Container
            backgroundImageUrl="url(image/flip-white.png)"
            backgroundOpacity={1}
            styleProps={{
              backgroundRepeat: 'repeat',
              backgroundSize: '6px 6px',
            }}
            className="rounded-lg bg-[#E1E3F2]/40"
          >
            <Card className="rounded-lg bg-transparent p-4">
              <h1 className="text-sm font-medium text-secondary dark:text-white">{orgName}</h1>
              <h2 className="mb-4 pt-2 text-lg font-medium text-primary dark:text-white">
                {project?.name || 'All Projects'}
              </h2>
            </Card>
          </Container>
          <DialogFooter className="flex flex-col gap-3 sm:justify-start">
            <Button
              className="rounded-lg bg-white px-3 py-5 text-secondary shadow-lg hover:bg-muted"
              onClick={closeDialog}
              autoFocus
              disabled={deleteMutation.isPending}
            >
              Second thoughts, no
            </Button>
            <Button
              className="rounded-lg bg-error px-3 py-5 text-white hover:bg-error dark:bg-error dark:hover:bg-error"
              onClick={() => {
                deleteMutation.mutate({ projectId: project.id });
              }}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : "Yes, I'm confident"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ProjectCard;
