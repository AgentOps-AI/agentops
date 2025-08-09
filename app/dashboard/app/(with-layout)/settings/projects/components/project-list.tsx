'use client';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Card, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { toast } from '@/components/ui/use-toast';
import {
  CheckmarkCircle01Icon as Check,
  Copy01Icon as Copy,
  PencilEdit01Icon as EditIcon,
  AddCircleIcon as PlusCircle,
  RefreshIcon as RefreshCw,
  Delete01Icon as Trash,
  Cancel01Icon as X,
  Loading03Icon,
  LockPasswordIcon,
} from 'hugeicons-react';
import { useState, useMemo } from 'react';
import { useProjects, projectsQueryKey } from '@/hooks/queries/useProjects';
import {
  createProjectAPI,
  deleteProjectAPI,
  renameProjectAPI,
  rotateApiKeyAPI,
  CreateProjectPayload,
  DeleteProjectPayload,
  RenameProjectPayload,
  RotateApiKeyPayload,
} from '@/lib/api/projects';
import { IProject } from '@/types/IProject';
import { UseMutationResult, useMutation, useQueryClient } from '@tanstack/react-query';
import { IOrg } from '@/types/IOrg';
import { useProject } from '@/app/providers/project-provider';
import { ApiKeyBox } from '@/components/ui/api-key-box';
import { PremiumUpsellBanner } from '@/components/ui/premium-upsell-banner';
import { SubscriptionBadge } from '@/components/ui/subscription-badge';
import { useOrgFeatures } from '@/hooks/useOrgFeatures';
import { UpsellModal } from '@/components/ui/upsell-modal';
import { Skeleton } from '@/components/ui/skeleton';

type CreateMutationResult = UseMutationResult<IProject, Error, CreateProjectPayload, unknown>;
type DeleteMutationResponse = { success: boolean; message?: string };
type DeleteMutationResult = UseMutationResult<
  DeleteMutationResponse,
  Error,
  DeleteProjectPayload,
  unknown
>;
type RenameMutationResult = UseMutationResult<IProject, Error, RenameProjectPayload, unknown>;
type RotateMutationResult = UseMutationResult<IProject, Error, RotateApiKeyPayload, unknown>;

const canEditProject = (role?: string | null) => {
  return role === 'owner' || role === 'admin';
};

interface SharedProjectListProps {
  projects: IProject[];
  newProject: boolean;
  setNewProject: (value: boolean) => void;
  newProjectName: string;
  setNewProjectName: (name: string) => void;
  copyApiKey: (apiKey: string, projectName: string) => void;
  orgId: string;
  editMode: boolean;
  setEditMode: (value: boolean) => void;
  createProjectMutation: CreateMutationResult;
  isCreatingProject: boolean;
  isLoadingProjects: boolean;
  currentUserRole?: string | null;
  isPro: boolean;
  selectedProjectId?: string;
}

export function ProjectList(props: { org: IOrg }) {
  const { data: projectsForOrg, isLoading: projectsLoading } = useProjects(props.org.id);
  const queryClient = useQueryClient();
  const [newProject, setNewProject] = useState<boolean>(false);
  const [newProjectName, setNewProjectName] = useState<string>('New Project');
  const { selectedProject } = useProject();
  const { permissions, isLoading: isPermissionsLoading } = useOrgFeatures();

  const isPro = props.org.prem_status === 'pro';
  const isCurrentOrg = selectedProject?.org_id === props.org.id;

  const canCreateMoreProjects = useMemo(() => {
    // First check if user has the proper role (admin or owner)
    if (!canEditProject(props.org.current_user_role)) return false;

    if (isPermissionsLoading || !permissions) return false;
    const maxProjects = permissions.projects.maxAllowed;
    const currentProjects = projectsForOrg?.length || 0;

    if (isPro) return true; // Pro users can create unlimited projects
    if (typeof maxProjects === 'number' && currentProjects >= maxProjects) {
      return false;
    }
    return true;
  }, [isPermissionsLoading, permissions, projectsForOrg, isPro, props.org.current_user_role]);

  const createProjectDisabledReason = useMemo(() => {
    if (isPermissionsLoading || !permissions) return 'Loading permissions...';

    // Check if user lacks proper role
    if (!canEditProject(props.org.current_user_role)) {
      return 'You must be an admin or owner to create projects in this organization.';
    }

    if (!canCreateMoreProjects) {
      const maxProjects = permissions.projects.maxAllowed;
      return `Project limit of ${maxProjects} reached. Upgrade to Pro for unlimited projects.`;
    }
    return '';
  }, [isPermissionsLoading, permissions, canCreateMoreProjects, props.org.current_user_role]);

  const shouldShowUpsellBanner = useMemo(() => {
    if (isPermissionsLoading || !permissions) return false;
    return (
      !canCreateMoreProjects &&
      !!createProjectDisabledReason &&
      createProjectDisabledReason.includes('Project limit')
    );
  }, [isPermissionsLoading, permissions, canCreateMoreProjects, createProjectDisabledReason]);

  const createProjectMutation: CreateMutationResult = useMutation({
    mutationFn: createProjectAPI,
    onSuccess: (createdProject) => {
      queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      toast({ title: 'Project Created', description: `Created ${createdProject.name}` });
      setNewProject(false);
      setNewProjectName('New Project');
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
      toast({
        title: '❌ Failed to Create Project',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  const [editMode, setEditMode] = useState<boolean>(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  const sharedProps: SharedProjectListProps = {
    projects: projectsForOrg ?? [],
    newProject,
    setNewProject,
    newProjectName,
    setNewProjectName,
    copyApiKey,
    orgId: props.org.id,
    editMode,
    setEditMode,
    createProjectMutation,
    isCreatingProject: createProjectMutation.isPending,
    isLoadingProjects: projectsLoading,
    currentUserRole: props.org.current_user_role,
    isPro,
    selectedProjectId: selectedProject?.id,
  };

  return (
    <>
      <Card data-testid={`projects-settings-org-card-${props.org.id}`}>
        <CardHeader className="pb-1 max-md:px-4">
          <CardTitle
            data-testid={`projects-settings-org-card-title-${props.org.id}`}
            className="flex items-center gap-2 text-sm font-normal"
          >
            {props.org.name}
            <SubscriptionBadge tier={props.org.prem_status} showUpgrade={false} />
            {shouldShowUpsellBanner && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      className="relative ml-2 flex h-6 items-center overflow-hidden rounded-md border border-[#DEE0F4] bg-gradient-to-r from-[#DEE0F4] to-[#A3A8C9] px-2 text-xs font-semibold text-[#141B34] hover:from-[#BFC4E0] hover:to-[#7B81A6] focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 dark:border-[#A3A8C9] dark:text-[#23263A]"
                      onClick={() => setShowUpgradeModal(true)}
                      type="button"
                    >
                      <style jsx>{`
                        @keyframes shine {
                          0% {
                            left: -60%;
                            opacity: 0.2;
                          }
                          20% {
                            opacity: 0.6;
                          }
                          50% {
                            left: 100%;
                            opacity: 0.6;
                          }
                          80% {
                            opacity: 0.2;
                          }
                          100% {
                            left: 100%;
                            opacity: 0;
                          }
                        }
                        .animate-shine {
                          position: absolute;
                          top: 0;
                          left: -60%;
                          width: 60%;
                          height: 100%;
                          background: linear-gradient(90deg, transparent, #bfc4e0 60%, transparent);
                          opacity: 0.7;
                          border-radius: 0.375rem;
                          animation: shine 2.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
                          pointer-events: none;
                        }
                      `}</style>
                      <span className="relative z-0">Upgrade to Pro</span>
                      <div className="animate-shine" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent
                    className="max-w-sm rounded-xl bg-primary/80 p-3 font-light text-[#EBECF8] backdrop-blur-md"
                    side="bottom"
                    sideOffset={8}
                  >
                    <div className="space-y-1">
                      <p className="font-semibold">Project limit reached</p>
                      <p className="text-xs">{createProjectDisabledReason}</p>
                    </div>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </CardTitle>
        </CardHeader>
        {projectsLoading ? (
          <div
            className="p-4 text-center"
            data-testid={`projects-settings-org-card-loading-${props.org.id}`}
          >
            Loading projects...
          </div>
        ) : (
          <>
            {!isPro && isCurrentOrg && projectsForOrg && projectsForOrg.length > 1 && (
              <div className="px-4 pb-0">
                <PremiumUpsellBanner
                  title="Unlock All Projects"
                  messages={[
                    'Hobby plan allows only 1 active project',
                    'Upgrade to Pro for unlimited projects and API keys',
                  ]}
                />
              </div>
            )}
            <div className="md:hidden" data-testid={`project-list-mobile-${props.org.id}`}>
              <ProjectListMobile {...sharedProps} />
            </div>
            <div className="hidden md:block" data-testid={`project-list-desktop-${props.org.id}`}>
              <ProjectListDesktop {...sharedProps} />
            </div>
          </>
        )}
        <CardFooter className="justify-center border-t p-4">
          {!newProject &&
            (canCreateMoreProjects ? (
              <Button
                size="sm"
                variant="ghost"
                className="gap-2"
                onClick={() => setNewProject(true)}
                onMouseDown={() => setNewProject(true)}
                data-testid={`projects-settings-button-create-new-project-${props.org.id}`}
              >
                <PlusCircle className="h-3.5 w-3.5" />
                Create New Project
              </Button>
            ) : (
              <>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span
                        tabIndex={0}
                        data-testid={`projects-settings-tooltip-create-new-project-trigger-${props.org.id}`}
                      >
                        <Button
                          size="sm"
                          variant="ghost"
                          className="cursor-not-allowed gap-2 opacity-75"
                          disabled
                          aria-disabled="true"
                          onClick={() => setShowUpgradeModal(true)}
                        >
                          <LockPasswordIcon className="mr-1 h-4 w-4" />
                          Create New Project
                        </Button>
                      </span>
                    </TooltipTrigger>
                    <TooltipContent
                      className="w-1/5 rounded-xl bg-primary/80 p-3 font-light text-[#EBECF8] backdrop-blur-md sm:ml-64 sm:w-72"
                      side="bottom"
                      sideOffset={8}
                      data-testid={`projects-settings-tooltip-create-new-project-content-${props.org.id}`}
                    >
                      {createProjectDisabledReason}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <UpsellModal
                  open={showUpgradeModal}
                  onOpenChange={setShowUpgradeModal}
                  title={
                    createProjectDisabledReason.includes('Project limit')
                      ? 'Project Limit Reached'
                      : 'Permission Required'
                  }
                  description={createProjectDisabledReason}
                />
              </>
            ))}
        </CardFooter>
      </Card>
    </>
  );
}

function ProjectListDesktop({
  projects,
  newProject,
  setNewProject,
  newProjectName,
  setNewProjectName,
  copyApiKey,
  orgId,
  editMode,
  setEditMode,
  createProjectMutation,
  isCreatingProject,
  isLoadingProjects,
  currentUserRole,
  isPro,
  selectedProjectId,
}: SharedProjectListProps) {
  if (isLoadingProjects) return null;
  return (
    <div className="hidden md:block">
      <Table>
        <TableHeader className="ml-2">
          <TableRow>
            <TableHead className="pl-6 md:w-[250px]">Name</TableHead>
            <TableHead className="">API Key</TableHead>
            <TableHead className="text-center">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {projects?.map((project, index) => {
            const shouldBlurRow = !isPro && projects.length > 1 && index > 0;
            return (
              <TableRow
                key={project.id}
                data-testid="project-row"
                data-project-name={project.name}
                className={shouldBlurRow ? 'pointer-events-none opacity-50' : ''}
              >
                <TableCell className="pl-6 font-semibold md:w-[250px]">
                  <ProjectName
                    project={project}
                    editMode={editMode}
                    setEditMode={setEditMode}
                    currentUserRole={currentUserRole}
                  />
                </TableCell>
                <TableCell className="font-semibold">
                  <div className="flex w-full items-center gap-3">
                    <ApiKeyBox apiKey={project.api_key} />
                    <div className="flex w-10 gap-3">
                      <Tooltip delayDuration={0}>
                        <TooltipTrigger asChild>
                          <div className="flex w-5 items-center">
                            <Copy
                              className="w-5 cursor-pointer hover:text-blue-600"
                              onClick={() => copyApiKey(project.api_key, project.name)}
                            />
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>Copy API Key</TooltipContent>
                      </Tooltip>
                      <Tooltip delayDuration={0}>
                        <TooltipTrigger asChild>
                          <div className="flex w-5 items-center">
                            <RotateApiKey project={project} currentUserRole={currentUserRole} />
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>Rotate API Key</TooltipContent>
                      </Tooltip>
                      <DeleteProject project={project} currentUserRole={currentUserRole} />
                    </div>
                  </div>
                </TableCell>
                <TableCell className="font-semibold">
                  <div className="flex justify-center">
                    <DeleteProject project={project} currentUserRole={currentUserRole} />
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
          {newProject && (
            <TableRow>
              <TableCell className="pl-6 font-semibold" colSpan={3}>
                <div className="flex w-full justify-center">
                  <div className="flex w-2/3 items-center">
                    <Input
                      value={newProjectName}
                      onChange={(e) => setNewProjectName(e.target.value)}
                      className="my-0 h-8 flex-grow py-0"
                      data-testid="new-project-input"
                      disabled={isCreatingProject}
                    />
                    <div className="ml-5 flex gap-2">
                      <Check
                        className={`w-5 ${isCreatingProject ? 'opacity-50' : 'cursor-pointer'}`}
                        data-testid="create-project-confirm"
                        onClick={() => {
                          const trimmedName = newProjectName.trim();
                          if (!isCreatingProject && trimmedName) {
                            // Check for duplicate name (case-insensitive)
                            const alreadyExists = projects.some(
                              (p) => p.name.toLowerCase() === trimmedName.toLowerCase(),
                            );
                            if (alreadyExists) {
                              toast({
                                title: '❌ Duplicate Name',
                                description:
                                  'A project with this name already exists in this organization.',
                                variant: 'destructive', // Optional: use destructive variant for errors
                              });
                              return; // Prevent mutation call
                            }
                            // Proceed with creation if name is unique
                            createProjectMutation.mutate({
                              org_id: orgId,
                              name: trimmedName,
                            });
                          } else if (!isCreatingProject && !trimmedName) {
                            // Optional: Add toast for empty name if desired, though backend might handle this
                            toast({
                              title: '❌ Invalid Name',
                              description: 'Project name cannot be empty.',
                              variant: 'destructive',
                            });
                          }
                        }}
                      />
                      <X
                        className={`w-5 ${isCreatingProject ? 'opacity-50' : 'cursor-pointer'}`}
                        data-testid="create-project-cancel"
                        onClick={() => {
                          if (!isCreatingProject) {
                            setNewProject(false);
                            setNewProjectName('New Project');
                          }
                        }}
                      />
                    </div>
                  </div>
                </div>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}

function ProjectListMobile({
  projects,
  newProject,
  setNewProject,
  newProjectName,
  setNewProjectName,
  copyApiKey,
  orgId,
  editMode,
  setEditMode,
  createProjectMutation,
  isCreatingProject,
  isLoadingProjects,
  currentUserRole,
  isPro,
  selectedProjectId,
}: SharedProjectListProps) {
  if (isLoadingProjects) {
    return (
      <div className="space-y-4 p-4">
        {/* Create 3 skeleton project items */}
        {[...Array(3)].map((_, index) => (
          <div key={index} className="space-y-2 border-b pb-4">
            <div className="flex w-full items-center justify-between">
              <Skeleton className="h-6 w-32" />
              <div className="flex items-center gap-2">
                <Skeleton className="h-5 w-5" />
                <Skeleton className="h-5 w-5" />
                <Skeleton className="h-5 w-5" />
              </div>
            </div>
            <Skeleton className="h-10 w-full" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      {projects?.map((project, index) => {
        const shouldBlurRow = !isPro && projects.length > 1 && index > 0;
        return (
          <div
            key={project.id}
            className={
              shouldBlurRow
                ? 'pointer-events-none space-y-2 border-b pb-4 opacity-50'
                : 'space-y-2 border-b pb-4'
            }
            data-testid="project-row"
            data-project-name={project.name}
          >
            <div className="flex w-full items-center justify-between">
              <ProjectName
                project={project}
                editMode={editMode}
                setEditMode={setEditMode}
                currentUserRole={currentUserRole}
              />
              {!editMode && (
                <div className="flex items-center gap-2">
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>
                      <div className="flex w-5 items-center">
                        <Copy
                          className="w-5 cursor-pointer hover:text-blue-600"
                          onClick={() => copyApiKey(project.api_key, project.name)}
                        />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>Copy API Key</TooltipContent>
                  </Tooltip>
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>
                      <div className="flex w-5 items-center">
                        <RotateApiKey project={project} currentUserRole={currentUserRole} />
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>Rotate API Key</TooltipContent>
                  </Tooltip>
                  <DeleteProject project={project} currentUserRole={currentUserRole} />
                </div>
              )}
            </div>
            <div className="flex w-full items-center gap-2">
              <ApiKeyBox apiKey={project.api_key} />
            </div>
          </div>
        );
      })}
      {newProject && (
        <div className="space-y-2">
          <Input
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            className="my-0 h-8 w-full py-0"
            data-testid="new-project-input"
            disabled={isCreatingProject}
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={() => {
                const trimmedName = newProjectName.trim();
                if (!isCreatingProject && trimmedName) {
                  const alreadyExists = projects.some(
                    (p) => p.name.toLowerCase() === trimmedName.toLowerCase(),
                  );
                  if (alreadyExists) {
                    toast({
                      title: '❌ Duplicate Name',
                      description: 'A project with this name already exists in this organization.',
                      variant: 'destructive',
                    });
                    return;
                  }
                  createProjectMutation.mutate({ org_id: orgId, name: trimmedName });
                } else if (!isCreatingProject && !trimmedName) {
                  toast({
                    title: '❌ Invalid Name',
                    description: 'Project name cannot be empty.',
                    variant: 'destructive',
                  });
                }
              }}
              disabled={isCreatingProject}
            >
              {isCreatingProject ? (
                <Loading03Icon className="mr-2 h-4 w-5 animate-spin" />
              ) : (
                <Check className="mr-2 h-4 w-5" />
              )}
              Create
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                if (!isCreatingProject) {
                  setNewProject(false);
                  setNewProjectName('New Project');
                }
              }}
              disabled={isCreatingProject}
            >
              <X className="mr-2 h-4 w-5" />
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function ProjectName(props: {
  project: IProject;
  editMode: boolean;
  setEditMode: (editing: boolean) => void;
  currentUserRole?: string | null;
}) {
  const queryClient = useQueryClient();
  const [inputName, setInputName] = useState(props.project.name);
  const canEdit = canEditProject(props.currentUserRole);

  const renameMutation: RenameMutationResult = useMutation({
    mutationFn: renameProjectAPI,
    onSuccess: (updatedProject, _variables) => {
      queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      toast({ title: 'Project Renamed', description: `Renamed to ${updatedProject.name}` });
      props.setEditMode(false);
    },
    onError: (error) => {
      toast({ title: '❌ Rename Error', description: error.message });
    },
  });

  return (
    <div className="text-md flex w-full items-center">
      {props.editMode ? (
        <div className="flex w-full items-center">
          <Input
            value={inputName}
            onChange={(e) => setInputName(e.target.value)}
            className="my-0 h-8 flex-1 py-0"
            disabled={renameMutation.isPending}
          />
          <div className="ml-2 flex flex-shrink-0 gap-2 sm:ml-4">
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <Check
                  className={`w-5 ${renameMutation.isPending ? 'opacity-50' : 'cursor-pointer'}`}
                  onClick={() => {
                    if (
                      inputName !== props.project.name &&
                      inputName.trim() &&
                      !renameMutation.isPending
                    ) {
                      renameMutation.mutate({
                        projectId: props.project.id,
                        newName: inputName.trim(),
                      });
                    } else if (!renameMutation.isPending) {
                      props.setEditMode(false);
                    }
                  }}
                />
              </TooltipTrigger>
              <TooltipContent>Accept Name Change</TooltipContent>
            </Tooltip>
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <X
                  className={`w-5 ${renameMutation.isPending ? 'opacity-50' : 'cursor-pointer'}`}
                  onClick={() => {
                    if (!renameMutation.isPending) {
                      setInputName(props.project.name);
                      props.setEditMode(false);
                    }
                  }}
                />
              </TooltipTrigger>
              <TooltipContent>Cancel Name Change</TooltipContent>
            </Tooltip>
          </div>
        </div>
      ) : (
        <>
          {props.project.name}
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <div className="flex w-5 items-center">
                <EditIcon
                  className={`ml-1 w-5 py-0 ${canEdit ? 'cursor-pointer hover:text-blue-600' : 'cursor-not-allowed opacity-50'
                    }`}
                  onClick={() => {
                    if (canEdit) {
                      setInputName(props.project.name);
                      props.setEditMode(true);
                    }
                  }}
                />
              </div>
            </TooltipTrigger>
            <TooltipContent>{canEdit ? 'Update Project Name' : 'Permission Denied'}</TooltipContent>
          </Tooltip>
        </>
      )}
    </div>
  );
}

function RotateApiKey(props: { project: IProject; currentUserRole?: string | null }) {
  const queryClient = useQueryClient();
  const canRotate = canEditProject(props.currentUserRole);

  const rotateMutation: RotateMutationResult = useMutation({
    mutationFn: rotateApiKeyAPI,
    onSuccess: (_projectResponse, _variables) => {
      queryClient.invalidateQueries({ queryKey: projectsQueryKey });
      toast({
        title: 'API Key Rotated Successfully',
        description: `Rotation confirmed for ${props.project.name}.`,
      });
    },
    onError: (error) => {
      console.error('Rotate API key error:', error);
      toast({ title: '❌ Failed to Rotate API Key', description: error.message });
    },
  });

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <div className="flex w-5 items-center">
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <RefreshCw
                className={`w-5 ${canRotate ? 'cursor-pointer hover:text-blue-600' : 'cursor-not-allowed opacity-50'
                  } ${rotateMutation.isPending ? 'animate-spin' : ''}`}
                onClick={(e) => {
                  if (!canRotate) e.preventDefault();
                }}
              />
            </TooltipTrigger>
            <TooltipContent>{canRotate ? 'Rotate API Key' : 'Permission Denied'}</TooltipContent>
          </Tooltip>
        </div>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Rotate your API Key?</AlertDialogTitle>
          <AlertDialogDescription>
            This action cannot be undone. This will permanently disable the current API Key for
            project &quot;{props.project.name}&quot; and issue a new one.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex flex-col gap-3 sm:justify-start">
          <AlertDialogCancel
            className="rounded-lg bg-white px-3 py-5 text-secondary shadow-lg hover:bg-muted"
            disabled={rotateMutation.isPending}
          >
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            className="rounded-lg bg-error px-3 py-5 text-white hover:bg-error dark:bg-error dark:hover:bg-error"
            onClick={() => {
              if (canRotate) {
                rotateMutation.mutate({ projectId: props.project.id });
              }
            }}
            disabled={rotateMutation.isPending || !canRotate}
          >
            {rotateMutation.isPending ? 'Rotating...' : 'Rotate API Key'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function DeleteProject(props: { project: IProject; currentUserRole?: string | null }) {
  const { selectedProject, setSelectedProject } = useProject();
  const queryClient = useQueryClient();
  const canDelete = canEditProject(props.currentUserRole);

  const deleteMutation: DeleteMutationResult = useMutation({
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
    onError: (error: Error, variables, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      if (context?.previousProjects) {
        queryClient.setQueryData(projectsQueryKey, context.previousProjects);
      }
      console.error('Delete project error:', error);
      toast({ title: `❌ Failed to delete ${props.project.name}`, description: error.message });
    },
    onSuccess: (data, variables) => {
      if (data.success) {
        if (selectedProject?.id === variables.projectId) {
          setSelectedProject(null);
        }
        toast({ title: 'Project Deleted', description: `Deleted ${props.project.name}` });
      } else {
        // Revert the optimistic update if the server indicates failure
        queryClient.invalidateQueries({ queryKey: projectsQueryKey });
        toast({
          title: `❌ Failed to delete ${props.project.name}`,
          description: data.message || 'Unknown error',
        });
      }
    },
    onSettled: () => {
      // Always refetch after error or success to ensure consistency
      queryClient.invalidateQueries({ queryKey: projectsQueryKey });
    },
  });

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Trash
          color="crimson"
          className={`w-5 ${canDelete ? 'hover:cursor-pointer' : 'cursor-not-allowed opacity-50'}`}
          data-testid="delete-project-trigger"
          onClick={(e) => {
            if (!canDelete) e.preventDefault();
          }}
        />
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete your project?</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete {props.project.name}? This action cannot be undone and
            all associated traces/data will be permanently erased.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex flex-col gap-3 sm:justify-start">
          <AlertDialogCancel
            className="rounded-lg bg-white px-3 py-5 text-secondary shadow-lg hover:bg-muted"
            disabled={deleteMutation.isPending}
          >
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            className="rounded-lg bg-error px-3 py-5 text-white hover:bg-error dark:bg-error dark:hover:bg-error"
            onClick={() => {
              if (canDelete) {
                deleteMutation.mutate({ projectId: props.project.id });
              }
            }}
            disabled={deleteMutation.isPending || !canDelete}
            data-testid="delete-project-confirm"
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete Project'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function copyApiKey(apiKey: string, projectName: string) {
  navigator.clipboard
    ?.writeText(apiKey)
    .then(() => {
      toast({
        title: 'API Key Copied to Clipboard',
        description: `Copied API key for ${projectName}`,
      });
    })
    .catch(() => {
      toast({
        title: '❌ Could Not Access Clipboard - Manually copy the API Key below:',
        description: apiKey,
      });
    });
}
