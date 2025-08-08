'use client';

import { useState } from 'react';
import { Button } from './button';
import { Input } from './input';
import { Popover, PopoverContent, PopoverTrigger } from './popover';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './select';
import { toast } from './use-toast';
import { Cancel01Icon as CloseIcon } from 'hugeicons-react';
import { useMutation, useQueryClient, UseMutationResult } from '@tanstack/react-query';
import {
  renameProjectAPI,
  RenameProjectPayload,
  createProjectAPI,
  CreateProjectPayload,
} from '@/lib/api/projects';
import { projectsQueryKey } from '@/hooks/queries/useProjects';
import { IOrg } from '@/types/IOrg';
import { IProject } from '@/types/IProject';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { LockIcon, PlusSignCircleIcon as PlusIcon } from 'hugeicons-react';
import { UpsellModal } from './upsell-modal';

export const ProjectDetails = ({
  orgs,
  project_id,
  project_name,
  org_name,
  isEdit,
  handleModalClose,
  lockedOrgId,
}: {
  orgs: IOrg[];
  project_id?: string;
  project_name?: string;
  org_name?: string;
  isEdit: boolean;
  handleModalClose: () => void;
  lockedOrgId?: string;
}) => {
  const queryClient = useQueryClient();
  const initialOrgId = lockedOrgId
    ? lockedOrgId
    : isEdit
      ? (orgs.find((o) => o.name === org_name)?.id ?? (orgs.length > 0 ? orgs[0].id : ''))
      : orgs.length > 0
        ? orgs[0].id
        : '';
  const [projectName, setProjectName] = useState(isEdit ? project_name : 'New Project');
  const [selectedOrgId, setSelectedOrgId] = useState<string>(initialOrgId);

  type RenameMutationResponse = IProject;
  type RenameMutationResult = UseMutationResult<
    RenameMutationResponse,
    Error,
    RenameProjectPayload,
    unknown
  >;

  type CreateMutationResult = UseMutationResult<IProject, Error, CreateProjectPayload, unknown>;

  const createProjectMutation: CreateMutationResult = useMutation({
    mutationFn: createProjectAPI,
    onSuccess: (createdProject) => {
      queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      toast({ title: 'Project Created', description: `Created ${createdProject.name}` });
      handleModalClose();
      if (typeof window !== 'undefined') {
        navigator.clipboard
          .writeText(createdProject.api_key)
          .then(() =>
            toast({
              title: 'API Key Copied',
              description: `Copied API key for ${createdProject.name}`,
            }),
          )
          .catch(() =>
            toast({ title: '❌ Manually copy API Key:', description: createdProject.api_key }),
          );
      }
    },
    onError: (error) => {
      console.error('Create project error:', error);
      toast({ title: '❌ Failed to Create Project', description: error.message });
    },
  });

  const renameMutation: RenameMutationResult = useMutation({
    mutationFn: renameProjectAPI,
    onSuccess: (updatedProject) => {
      queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      toast({ title: 'Project Renamed', description: `Renamed to ${updatedProject.name}` });
      handleModalClose();
    },
    onError: (error) => {
      console.error('Rename project error:', error);
      toast({ title: '❌ Failed to Rename Project', description: error.message });
    },
  });

  async function createProject() {
    if (!projectName?.trim()) {
      toast({ title: '❌ Invalid Input', description: 'Project name cannot be empty' });
      return;
    }
    if (!selectedOrgId) {
      toast({ title: '❌ Invalid Input', description: 'Please select an organization' });
      return;
    }

    createProjectMutation.mutate({ org_id: selectedOrgId, name: projectName.trim() });
  }

  async function updateProjectInfo() {
    if (!projectName?.trim()) {
      toast({ title: '❌ Invalid Input', description: 'Project name cannot be empty' });
      return;
    }
    if (!project_id) {
      console.error('Cannot rename project without an ID');
      toast({ title: '❌ Error', description: 'Cannot rename project: Missing ID' });
      return;
    }

    renameMutation.mutate({ projectId: project_id, newName: projectName });
  }

  return (
    <div>
      <div className="mb-5 text-sm font-medium text-secondary dark:text-white">
        {isEdit
          ? 'Update project'
          : lockedOrgId
            ? `Create a project in ${orgs.find((o) => o.id === lockedOrgId)?.name || 'this organization'}`
            : 'Create a project'}
      </div>
      <div className="mb-2 text-sm font-medium text-secondary dark:text-white">Project Name</div>
      <Input
        id="projectName"
        type="text"
        value={projectName}
        className="rounded-lg bg-[#E1E3F2] py-5 hover:bg-[#D8DAED]"
        onChange={(e) => setProjectName(e.target.value)}
      />
      {!lockedOrgId && (
        <Select onValueChange={setSelectedOrgId} defaultValue={selectedOrgId} disabled={isEdit}>
          <SelectTrigger className="mt-5 w-full rounded-lg border-4 py-5">
            <SelectValue placeholder="Organization" />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              {orgs?.map((org) => (
                <SelectItem key={org.id} value={org.id}>
                  {org.name}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      )}
      <Button
        type="button"
        disabled={
          (isEdit && renameMutation.isPending) || (!isEdit && createProjectMutation.isPending)
        }
        onClick={isEdit ? updateProjectInfo : createProject}
        className="mb-2 mt-5 flex w-full items-center justify-center rounded-lg bg-primary p-6 text-sm font-light text-white"
      >
        {isEdit
          ? renameMutation.isPending
            ? 'Updating...'
            : 'Update'
          : createProjectMutation.isPending
            ? 'Creating...'
            : 'Create'}{' '}
        project
      </Button>
    </div>
  );
};

interface CreateProjectCardProps {
  orgs: IOrg[];
  isDisabled?: boolean;
  disabledTooltipContent?: string;
}

export const CreateProjectCard = ({
  orgs,
  isDisabled,
  disabledTooltipContent,
}: CreateProjectCardProps) => {
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);
  const [showUpsellModal, setShowUpsellModal] = useState(false);

  const handleButtonClick = () => {
    if (isDisabled) {
      setShowUpsellModal(true);
    } else {
      setIsPopoverOpen(!isPopoverOpen);
    }
  };

  const triggerButton = (
    <Button
      size="icon"
      variant="icon"
      disabled={isDisabled}
      onClick={handleButtonClick}
      className={isDisabled ? 'opacity-75' : ''}
    >
      {isDisabled ? <LockIcon className="h-4 w-4" /> : isPopoverOpen ? <CloseIcon /> : <PlusIcon />}
    </Button>
  );

  return (
    <div>
      {isDisabled ? (
        <>
          <TooltipProvider delayDuration={100}>
            <Tooltip>
              <TooltipTrigger asChild>{triggerButton}</TooltipTrigger>
              <TooltipContent>
                <p>{disabledTooltipContent}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <UpsellModal
            open={showUpsellModal}
            onOpenChange={setShowUpsellModal}
            title="Project Limit Reached"
            description={disabledTooltipContent || 'Upgrade your plan to create more projects.'}
          />
        </>
      ) : (
        <Popover open={isPopoverOpen} onOpenChange={setIsPopoverOpen}>
          <PopoverTrigger asChild>{triggerButton}</PopoverTrigger>
          <PopoverContent
            className="mr-[120px] rounded-lg border border-white bg-[#F7F8FF] px-5 py-5 shadow-md"
            sideOffset={8}
          >
            <ProjectDetails
              orgs={orgs}
              isEdit={false}
              handleModalClose={() => setIsPopoverOpen(false)}
            />
          </PopoverContent>
        </Popover>
      )}
    </div>
  );
};
