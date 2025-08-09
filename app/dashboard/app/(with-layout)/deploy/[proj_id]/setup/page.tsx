"use client"
import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useDeployment, useDeployments } from '@/hooks/queries/useProjects';
import { IHostingProject } from '@/types/IProject';
import { GitHubLogoIcon } from '@radix-ui/react-icons';
import { Alert01Icon as WarningIcon, Delete01Icon as TrashIcon } from 'hugeicons-react';
import EditableField from '@/components/ui/EditableField';
import RepoDropdown from './RepoDropdown';
import SecretsManager from './SecretsManager';
import { SkeletonHeader, SkeletonCard, SkeletonSourceCode, SkeletonDeployService } from './Skeletons';

function ProjectHeader({ project, proj_id }: { project: any, proj_id: string }) {
  const router = useRouter();

  const handleBackClick = () => {
    router.push(`/deploy/${proj_id}`);
  };

  return (
    <div className="relative">
      <button
        onClick={handleBackClick}
        className="flex items-center gap-2 px-3 py-2 text-[14px] font-medium text-[rgba(20,27,52,0.74)] hover:text-[rgba(20,27,52,1)] hover:bg-[rgba(248,249,250,1)] rounded-md transition-colors mb-4"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M10 12L6 8L10 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        Back
      </button>
      <div className="flex items-center gap-3 mt-5 mb-1">
        <h1 className="text-[32px] font-bold">{project?.name}</h1>
        <span className="flex items-center gap-1 ml-3">
          <span className="inline-block w-3 h-3 rounded-full animate-pulse" style={{ background: 'rgba(75,196,152,1)', animation: 'fadeInOut 2.5s ease-in-out infinite' }}></span>
          <span className="text-[16px] font-medium text-[rgba(75,196,152,1)]">Running</span>
        </span>
      </div>
      <div className="text-[24px] text-[rgba(20,27,52,0.74)] mb-10">
        {project?.org?.name} Organization
      </div>
    </div>
  );
}

// Simple modal component
function Modal({ open, onClose, onConfirm, children }: { open: boolean, onClose: () => void, onConfirm: () => void, children: React.ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
      <div className="bg-white rounded-lg shadow-lg p-6 min-w-[320px] max-w-[90vw]">
        <div className="mb-6">{children}</div>
        <div className="flex justify-end gap-2">
          <button
            className="px-4 py-2 rounded border border-[rgba(222,224,244,1)] bg-white text-[14px] font-medium hover:bg-[rgba(248,249,250,1)] transition-colors"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="px-4 py-2 rounded bg-[rgba(230,90,126,1)] text-white text-[14px] font-medium hover:bg-[rgba(200,60,96,1)] transition-colors"
            onClick={onConfirm}
          >
            Change Repository
          </button>
        </div>
      </div>
    </div>
  );
}

// Delete confirmation modal component
function DeleteModal({ open, onClose, onConfirm, projectName }: { open: boolean, onClose: () => void, onConfirm: () => void, projectName: string }) {
  const [deleteText, setDeleteText] = React.useState('');
  const isConfirmEnabled = deleteText === 'delete';

  const handleConfirm = () => {
    if (isConfirmEnabled) {
      onConfirm();
      setDeleteText('');
    }
  };

  const handleClose = () => {
    onClose();
    setDeleteText('');
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
      <div className="bg-white rounded-lg shadow-lg p-6 min-w-[400px] max-w-[90vw]">
        <div className="mb-6">
          <div className="text-[16px] font-semibold mb-2 text-[rgba(230,90,126,1)]">Delete Deployment</div>
          <div className="text-[14px] text-[rgba(20,27,52,0.74)] mb-4">
            This action cannot be undone. This will permanently delete the deployment <strong>{projectName}</strong> and all associated data.
          </div>
          <div className="mb-4">
            <label className="block text-[14px] font-medium text-[rgba(20,27,52,1)] mb-2">
              Type {'"'}delete{'"'} to confirm:
            </label>
            <input
              type="text"
              value={deleteText}
              onChange={(e) => setDeleteText(e.target.value)}
              className="w-full px-3 py-2 border border-[rgba(222,224,244,1)] rounded-md text-[14px] focus:outline-none focus:ring-2 focus:ring-[rgba(230,90,126,0.2)] focus:border-[rgba(230,90,126,1)]"
              placeholder="delete"
            />
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <button
            className="px-4 py-2 rounded border border-[rgba(222,224,244,1)] bg-white text-[14px] font-medium hover:bg-[rgba(248,249,250,1)] transition-colors"
            onClick={handleClose}
          >
            Cancel
          </button>
          <button
            className={`px-4 py-2 rounded text-[14px] font-medium transition-colors ${
              isConfirmEnabled
                ? 'bg-[rgba(230,90,126,1)] text-white hover:bg-[rgba(200,60,96,1)]'
                : 'bg-[rgba(222,224,244,1)] text-[rgba(20,27,52,0.5)] cursor-not-allowed'
            }`}
            onClick={handleConfirm}
            disabled={!isConfirmEnabled}
          >
            Delete Deployment
          </button>
        </div>
      </div>
    </div>
  );
}

export default function DeployProjectSetupPage() {
  const params = useParams();
  const router = useRouter();
  const proj_id = params.proj_id as string;
  const { deployment, isLoading, error } = useDeployment(proj_id);
  const { refetch: refetchDeployments } = useDeployments();
  const [isRepoLoading, setIsRepoLoading] = React.useState(false);
  const [repos, setRepos] = React.useState<any[] | null>(null);
  const [dropdownOpen, setDropdownOpen] = React.useState(false);
  const [pendingRepo, setPendingRepo] = React.useState<any | null>(null);
  const [showChangeRepoModal, setShowChangeRepoModal] = React.useState(false);
  const [isRedeploying, setIsRedeploying] = React.useState(false);
  const [showDeleteModal, setShowDeleteModal] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);

  // Pack configurations
  const packConfigurations = {
    FASTAPI: {
      name: 'FastAPI',
      description: 'This pack expects a FastAPI application to exist in the repository and will serve the existing endpoints.'
    },
    CREWAI: {
      name: 'CrewAI',
      description: 'This pack expects a CrewAI agent to exist in the repository and will search inside the watch_path for the kickoff method and expose it as an API endpoint.'
    },
    CREWAI_JOB: {
      name: 'CrewAI Job',
      description: 'This pack expects a CrewAI agent to exist in the repository and will search inside the watch_path for the kickoff method and run it as a one-time job.'
    }
  };

  // State for editable fields
  const [editingField, setEditingField] = React.useState<string | null>(null);
  const [fieldValues, setFieldValues] = React.useState({
    entrypoint: '',
    watch_path: '',
    user_callback_url: '',
    pack_name: ''
  });
  const [originalFieldValues, setOriginalFieldValues] = React.useState({
    entrypoint: '',
    watch_path: '',
    user_callback_url: '',
    pack_name: ''
  });

  // Helper to type-narrow deployment to IHostingProject
  const hostingDeployment = deployment as IHostingProject | undefined;

  // Initialize field values from deployment data
  React.useEffect(() => {
    if (hostingDeployment) {
      const initialValues = {
        entrypoint: hostingDeployment.entrypoint || '',
        watch_path: hostingDeployment.watch_path || '',
        user_callback_url: hostingDeployment.user_callback_url || '',
        pack_name: hostingDeployment.pack_name || 'FASTAPI'
      };
      setFieldValues(initialValues);
      setOriginalFieldValues(initialValues);
    }
  }, [hostingDeployment]);

  const handleSelectRepo = async () => {
    if (!hostingDeployment) return;
    setIsRepoLoading(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    try {
      const res = await fetch(`${apiUrl}/deploy/github/repos?project_id=${encodeURIComponent(hostingDeployment.id)}`, {
        method: 'GET',
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setRepos(data.repos || data); // support both {repos: []} and []
      }
    } catch (err) {
      console.error('Failed to select repo', err);
    } finally {
      setIsRepoLoading(false);
    }
  };

  // Group repos by organization for dropdown using repo.full_name
  const orgsWithRepos = React.useMemo(() => {
    if (!repos) return [];
    const orgMap: Record<string, any[]> = {};
    repos.forEach((repo: any) => {
      const fullName = repo.full_name || '';
      const orgName = fullName.split('/')[0] || 'Other';
      if (!orgMap[orgName]) orgMap[orgName] = [];
      orgMap[orgName].push(repo);
    });
    return Object.entries(orgMap).map(([org, repos]) => ({ org, repos }));
  }, [repos]);

  async function updateDeployment(changes: Partial<IHostingProject>) {
    if (!hostingDeployment) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const deploymentData = { ...hostingDeployment, ...changes };
    try {
      await fetch(`${apiUrl}/deploy/deployments/${hostingDeployment.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(deploymentData),
      });
      // Optionally, update UI or refetch project
      console.log('Deployment updated with changes:', changes);
    } catch (err) {
      console.error('Failed to update deployment:', err);
    }
  }

  const handleRepoSelect = (repo: any) => {
    if (hostingDeployment && hostingDeployment.git_url) {
      setPendingRepo(repo);
      setShowChangeRepoModal(true);
    } else {
      updateDeployment({ git_url: `https://github.com/${repo.full_name}` });
      refetchDeployments();
    }
  };

  const handleConfirmChangeRepo = () => {
    setShowChangeRepoModal(false);
    setPendingRepo(null);
    if (hostingDeployment) {
      updateDeployment({ git_url: '' });
    }
    // Refetch deployments to update the UI
    refetchDeployments?.();
    handleSelectRepo();
    setDropdownOpen(true);
  };

  const handleCancelChangeRepo = () => {
    setShowChangeRepoModal(false);
    setPendingRepo(null);
  };

  // Editable field handlers
  const handleFieldEdit = (fieldKey: string) => {
    setEditingField(fieldKey);
  };

  const handleFieldSave = (fieldKey: string, value: string) => {
    const updatedValues = { ...fieldValues, [fieldKey]: value };
    setFieldValues(updatedValues);
    setEditingField(null);

    // Call updateDeployment with the specific field
    const deploymentChanges: any = {};
    deploymentChanges[fieldKey] = value;
    updateDeployment(deploymentChanges);
  };

  const handleFieldCancel = () => {
    setEditingField(null);
  };

  const handleFieldChange = (fieldKey: string, value: string) => {
    setFieldValues(prev => ({ ...prev, [fieldKey]: value }));
  };

  // Check if any changes have been made
  const hasChanges = React.useMemo(() => {
    return Object.keys(fieldValues).some(key =>
      fieldValues[key as keyof typeof fieldValues] !== originalFieldValues[key as keyof typeof originalFieldValues]
    );
  }, [fieldValues, originalFieldValues]);

  const handleRedeploy = async () => {
    if (!hostingDeployment) return;

    setIsRedeploying(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    try {
      const response = await fetch(`${apiUrl}/deploy/deployments/${hostingDeployment.id}/launch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Deployment initiated successfully:', result);

        // Navigate back to the main deploy page
        router.push(`/deploy/${proj_id}`);
      } else {
        console.error('Failed to initiate deployment:', response.status, response.statusText);
        // You might want to show an error message to the user here
      }
    } catch (err) {
      console.error('Error initiating deployment:', err);
      // You might want to show an error message to the user here
    } finally {
      setIsRedeploying(false);
    }
  };

  const handleDelete = async () => {
    if (!hostingDeployment) return;

    setIsDeleting(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    try {
      const response = await fetch(`${apiUrl}/deploy/deployments/${hostingDeployment.id}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (response.ok) {
        console.log('Deployment deleted successfully');

        // Refetch deployments to update the list before redirecting
        await refetchDeployments?.();

        // Navigate back to the main deploy page
        router.push('/deploy');
      } else {
        console.error('Failed to delete deployment:', response.status, response.statusText);
        // You might want to show an error message to the user here
      }
    } catch (err) {
      console.error('Error deleting deployment:', err);
      // You might want to show an error message to the user here
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  const handleDeleteClick = () => {
    setShowDeleteModal(true);
  };

  const handleDeleteCancel = () => {
    setShowDeleteModal(false);
  };

  let content;
  if (isLoading) {
    content = (
      <>
        <SkeletonHeader />
        <SkeletonSourceCode />
        <SkeletonCard />
        <SkeletonDeployService />
      </>
    );
  } else if (error) {
    content = <div className="text-[rgba(230,90,126,1)] font-['Figtree'] text-[16px]">Error loading project.</div>;
  } else if (!hostingDeployment) {
    content = <div className="text-[rgba(230,90,126,1)] font-['Figtree'] text-[16px]">Project not found.</div>;
  } else {
    content = <ProjectHeader project={hostingDeployment} proj_id={proj_id} />;
  }

  return (
    <div className="font-['Figtree'] text-[rgba(20,27,52,1)] mx-8 my-8">
      {content}
      {!isLoading && (
        <>
          {/* Source Code Section */}
          <section className="mb-8 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm relative">
        <h2 className="text-[16px] font-semibold text-[rgba(20,27,52,1)] mb-4">Source Code</h2>
        {hostingDeployment && !hostingDeployment.git_url && !repos && (
          <button
            className="font-['Figtree'] text-[14px] px-4 py-2 bg-[rgba(248,249,250,1)] text-[rgba(20,27,52,1)] border border-[rgba(222,224,244,1)] rounded-md font-medium hover:bg-[rgba(222,224,244,1)] transition-colors"
            onClick={handleSelectRepo}
            disabled={isRepoLoading}
          >
            {isRepoLoading ? 'Loading...' : 'Select GitHub repository'}
          </button>
        )}
        {repos && !hostingDeployment?.git_url && (
          <div className="relative">
            <button
              className="font-['Figtree'] text-[14px] px-4 py-2 bg-[rgba(248,249,250,1)] text-[rgba(20,27,52,1)] border border-[rgba(222,224,244,1)] rounded-md font-medium hover:bg-[rgba(222,224,244,1)] transition-colors"
              onClick={() => setDropdownOpen((open) => !open)}
            >
              {dropdownOpen ? 'Hide repositories' : 'Select a repository'}
            </button>
            <RepoDropdown
              orgsWithRepos={orgsWithRepos}
              onSelect={handleRepoSelect}
              isOpen={dropdownOpen}
              onClose={() => setDropdownOpen(false)}
            />
          </div>
        )}
        {hostingDeployment && hostingDeployment.git_url && (
          <div className="flex flex-col gap-2 mt-2">
            <div className="font-['Figtree'] text-[14px] text-[rgba(20,27,52,1)] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span>Selected repository:</span>
                <span className="font-semibold flex items-center gap-1">
                  <GitHubLogoIcon className="w-4 h-4"/>
                  {hostingDeployment.git_url.replace('https://github.com/', '')}
                </span>
              </div>
              <button
                className="w-6 h-6 flex items-center justify-center text-[rgba(20,27,52,0.5)] hover:text-[rgba(230,90,126,1)] hover:bg-[rgba(222,224,244,0.5)] rounded transition-colors"
                onClick={() => setShowChangeRepoModal(true)}
                title="Change repository"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M1 1L13 13M1 13L13 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </button>
            </div>
          </div>
        )}
        <Modal open={showChangeRepoModal} onClose={handleCancelChangeRepo} onConfirm={handleConfirmChangeRepo}>
          <div className="text-[16px] font-semibold mb-2">Change Repository?</div>
          <div className="text-[14px] text-[rgba(20,27,52,0.74)]">
            Selecting a new repository will redeploy your agent with new code. This is a destructive change.
          </div>
        </Modal>
        <DeleteModal
          open={showDeleteModal}
          onClose={handleDeleteCancel}
          onConfirm={handleDelete}
          projectName={hostingDeployment?.name || 'this deployment'}
        />
      </section>
      {/* Configuration Fields Section */}
      <section className="mb-8 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
        <h2 className="text-[16px] font-semibold text-[rgba(20,27,52,1)] mb-4">Configuration</h2>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-[14px] font-medium text-[rgba(20,27,52,1)]">App Type</label>
            <select
              value={fieldValues.pack_name}
              onChange={(e) => {
                const newValue = e.target.value;
                setFieldValues(prev => ({ ...prev, pack_name: newValue }));
                handleFieldSave('pack_name', newValue);
              }}
              className="w-full px-3 py-2 border border-[rgba(222,224,244,1)] rounded-md text-[14px] focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {Object.entries(packConfigurations).map(([key, config]) => (
                <option key={key} value={key}>{config.name}</option>
              ))}
            </select>
            <p className="text-[12px] text-[rgba(20,27,52,0.6)]">
              {packConfigurations[fieldValues.pack_name as keyof typeof packConfigurations]?.description || 'Select an app type to see description'}
            </p>
          </div>

          <EditableField
            label="Entrypoint"
            value={fieldValues.entrypoint}
            placeholder="e.g. main.py"
            fieldKey="entrypoint"
            isEditing={editingField === 'entrypoint'}
            onEdit={() => handleFieldEdit('entrypoint')}
            onSave={(value) => handleFieldSave('entrypoint', value)}
            onCancel={handleFieldCancel}
            onChange={(value) => handleFieldChange('entrypoint', value)}
          />
          <EditableField
            label="Watch Path"
            value={fieldValues.watch_path}
            placeholder="e.g. /src"
            fieldKey="watch_path"
            isEditing={editingField === 'watch_path'}
            onEdit={() => handleFieldEdit('watch_path')}
            onSave={(value) => handleFieldSave('watch_path', value)}
            onCancel={handleFieldCancel}
            onChange={(value) => handleFieldChange('watch_path', value)}
          />
          <EditableField
            label="User Callback URL"
            value={fieldValues.user_callback_url}
            placeholder="e.g. https://api.example.com/webhook"
            fieldKey="user_callback_url"
            isEditing={editingField === 'user_callback_url'}
            onEdit={() => handleFieldEdit('user_callback_url')}
            onSave={(value) => handleFieldSave('user_callback_url', value)}
            onCancel={handleFieldCancel}
            onChange={(value) => handleFieldChange('user_callback_url', value)}
          />
        </div>
      </section>
              {hasChanges && (
          <div className="mb-8 flex justify-center">
                          <button
                onClick={handleRedeploy}
                disabled={isRedeploying}
                className="px-6 py-3 bg-blue-600 text-white text-[14px] font-medium rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  animation: isRedeploying ? 'none' : 'glowPulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                }}
              >
                <style jsx>{`
                  @keyframes glowPulse {
                    0%, 100% {
                      box-shadow: 0 0 20px rgba(59, 130, 246, 0.5), 0 0 40px rgba(59, 130, 246, 0.3);
                    }
                    50% {
                      box-shadow: 0 0 30px rgba(59, 130, 246, 0.7), 0 0 60px rgba(59, 130, 246, 0.5);
                    }
                  }
                `}</style>
                {isRedeploying ? 'Deploying...' : 'Redeploy'}
              </button>
          </div>
        )}
      {/* Environment Variables Section */}
      <SecretsManager projectId={proj_id} />

      <section className="mb-8 mt-4 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
        <h2 className="text-[16px] font-semibold text-[rgba(20,27,52,1)] mb-2">Configure Deploy Service</h2>
        <p className="text-[14px] text-[rgba(20,27,52,0.74)] mb-0">
          {hostingDeployment ? JSON.stringify(hostingDeployment, null, 2) : 'No deployment data'}
        </p>
        {/* Add configuration form or steps here */}
      </section>
      {/* Danger Zone */}
      <section className="mb-8 border border-[rgba(230,90,126,0.3)] rounded-lg bg-[rgba(230,90,126,0.02)] p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <WarningIcon className="w-5 h-5 text-[rgba(230,90,126,1)]" />
          <h2 className="text-[16px] font-semibold text-[rgba(230,90,126,1)]">Danger!</h2>
        </div>
        <div className="mb-4">
          <p className="text-[14px] text-[rgba(20,27,52,0.74)] mb-2">
            Once you delete a deployment, there is no going back. Please be certain.
          </p>
        </div>
        <button
          onClick={handleDeleteClick}
          disabled={isDeleting}
          className="px-4 py-2 bg-[rgba(230,90,126,1)] text-white text-[14px] font-medium rounded-md hover:bg-[rgba(200,60,96,1)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <TrashIcon className="w-4 h-4" />
          {isDeleting ? 'Deleting...' : 'Delete Deployment'}
        </button>
      </section>
        </>
      )}
    </div>
  );
}