"use client"
import React from 'react';
import { useParams } from 'next/navigation';
import { useDeployment, useDeployments } from '@/hooks/queries/useProjects';
import { IHostingProject } from '@/types/IProject';
import { GitHubLogoIcon } from '@radix-ui/react-icons';
import EditableField from '@/components/ui/EditableField';

// Skeleton components
function SkeletonHeader() {
  return (
    <div className="relative">
      <div className="flex items-center gap-3 mt-5 mb-1">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse"></div>
        <div className="flex items-center gap-1 ml-3">
          <div className="w-3 h-3 bg-gray-200 rounded-full animate-pulse"></div>
          <div className="h-4 w-16 bg-gray-200 rounded animate-pulse"></div>
        </div>
      </div>
      <div className="h-6 w-64 bg-gray-200 rounded animate-pulse mb-10"></div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="mb-8 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
      <div className="h-5 w-32 bg-gray-200 rounded animate-pulse mb-4"></div>
      <div className="space-y-4">
        <div className="h-4 w-24 bg-gray-200 rounded animate-pulse"></div>
        <div className="h-10 w-full bg-gray-200 rounded animate-pulse"></div>
        <div className="h-4 w-32 bg-gray-200 rounded animate-pulse"></div>
        <div className="h-10 w-full bg-gray-200 rounded animate-pulse"></div>
        <div className="h-4 w-28 bg-gray-200 rounded animate-pulse"></div>
        <div className="h-10 w-full bg-gray-200 rounded animate-pulse"></div>
      </div>
    </div>
  );
}

function SkeletonSourceCode() {
  return (
    <div className="mb-8 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
      <div className="h-5 w-24 bg-gray-200 rounded animate-pulse mb-4"></div>
      <div className="h-10 w-48 bg-gray-200 rounded animate-pulse"></div>
    </div>
  );
}

function SkeletonDeployService() {
  return (
    <div className="mb-8 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
      <div className="h-5 w-40 bg-gray-200 rounded animate-pulse mb-2"></div>
      <div className="h-4 w-full bg-gray-200 rounded animate-pulse mb-2"></div>
      <div className="h-4 w-3/4 bg-gray-200 rounded animate-pulse"></div>
    </div>
  );
}

function ProjectHeader({ project, proj_id }: { project: any, proj_id: string }) {
  return (
    <div className="relative">
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

// Reusable dropdown for selecting a repo, grouped by organization
interface RepoDropdownProps {
  orgsWithRepos: Array<{ org: string; repos: any[] }>;
  onSelect: (repo: any) => void;
  isOpen: boolean;
  onClose: () => void;
}

function RepoDropdown({ orgsWithRepos, onSelect, isOpen, onClose }: RepoDropdownProps) {
  const [filter, setFilter] = React.useState('');

  if (!isOpen) return null;

  // Filter organizations and repos based on the filter text
  const filteredOrgsWithRepos = React.useMemo(() => {
    if (!filter.trim()) return orgsWithRepos;
    
    return orgsWithRepos.map(org => ({
      ...org,
      repos: org.repos.filter(repo => {
        const repoName = (repo.full_name || '').split('/')[1] || repo.full_name || repo.name;
        const orgName = org.org;
        return orgName.toLowerCase().includes(filter.toLowerCase()) ||
               repoName.toLowerCase().includes(filter.toLowerCase()) ||
               (repo.full_name || '').toLowerCase().includes(filter.toLowerCase());
      })
    })).filter(org => org.repos.length > 0);
  }, [orgsWithRepos, filter]);

  const clearFilter = () => {
    setFilter('');
  };

  return (
    <div className="absolute z-20 mt-2 w-96 max-h-80 bg-white border border-[rgba(222,224,244,1)] rounded shadow-lg">
      {/* Filter input */}
      <div className="p-3 border-b border-[rgba(222,224,244,1)]">
        <div className="relative">
          <input
            type="text"
            placeholder="Filter repositories..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full px-3 py-2 pr-8 text-[14px] border border-[rgba(222,224,244,1)] rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            autoFocus
          />
          {filter && (
            <button
              onClick={clearFilter}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 flex items-center justify-center text-[rgba(20,27,52,0.5)] hover:text-[rgba(230,90,126,1)] transition-colors"
              title="Clear filter"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M1 1L11 11M1 11L11 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>
          )}
        </div>
      </div>
      
      {/* Scrollable repo list */}
      <div className="max-h-64 overflow-y-auto p-2">
        {filteredOrgsWithRepos.length === 0 && (
          <div className="text-[14px] text-[rgba(230,90,126,1)]">
            {filter ? 'No repositories match your filter.' : 'No repositories found.'}
          </div>
        )}
        {filteredOrgsWithRepos.map((org) => (
          <div key={org.org} className="mb-2">
            <div className="font-semibold text-[15px] text-[rgba(20,27,52,1)] mb-1">{org.org}</div>
            {org.repos.map((repo) => {
              const repoName = (repo.full_name || '').split('/')[1] || repo.full_name || repo.name;
              return (
                <div
                  key={repo.id || repo.full_name}
                  className="ml-4 p-2 flex items-center gap-2 cursor-pointer hover:bg-[rgba(222,224,244,0.5)] rounded text-[14px]"
                  onClick={() => { onSelect(repo); onClose(); }}
                >
                  {/* GitHub logo SVG */}
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="shrink-0"><path fillRule="evenodd" clipRule="evenodd" d="M8 1.333c-3.682 0-6.667 2.985-6.667 6.667 0 2.946 1.91 5.444 4.557 6.333.333.06.456-.144.456-.32 0-.158-.006-.577-.009-1.133-1.855.403-2.247-.894-2.247-.894-.303-.77-.74-.975-.74-.975-.605-.414.046-.406.046-.406.67.047 1.022.688 1.022.688.595 1.02 1.56.726 1.94.555.06-.431.233-.726.424-.893-1.482-.168-3.04-.741-3.04-3.297 0-.728.26-1.323.687-1.79-.069-.168-.298-.846.065-1.764 0 0 .56-.18 1.833.684a6.37 6.37 0 0 1 1.667-.224c.566.003 1.137.077 1.667.224 1.272-.864 1.832-.684 1.832-.684.364.918.135 1.596.066 1.764.428.467.686 1.062.686 1.79 0 2.56-1.56 3.127-3.048 3.292.24.207.454.617.454 1.244 0 .898-.008 1.623-.008 1.844 0 .178.12.384.46.319C12.76 13.444 14.667 10.946 14.667 8c0-3.682-2.985-6.667-6.667-6.667Z" fill="#181717"/></svg>
                  {repoName}
                </div>
              );
            })}
          </div>
        ))}
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

export default function DeployProjectSetupPage() {
  const params = useParams();
  const proj_id = params.proj_id as string;
  const { deployment, isLoading, error } = useDeployment(proj_id);
  const { refetch: refetchDeployments } = useDeployments();
  const [isRepoLoading, setIsRepoLoading] = React.useState(false);
  const [repos, setRepos] = React.useState<any[] | null>(null);
  const [dropdownOpen, setDropdownOpen] = React.useState(false);
  const [pendingRepo, setPendingRepo] = React.useState<any | null>(null);
  const [showChangeRepoModal, setShowChangeRepoModal] = React.useState(false);

  // State for editable fields
  const [editingField, setEditingField] = React.useState<string | null>(null);
  const [fieldValues, setFieldValues] = React.useState({
    entrypoint: '',
    watch_path: '',
    user_callback_url: ''
  });
  const [originalFieldValues, setOriginalFieldValues] = React.useState({
    entrypoint: '',
    watch_path: '',
    user_callback_url: ''
  });

  // Helper to type-narrow deployment to IHostingProject
  const hostingDeployment = deployment as IHostingProject | undefined;

  // Initialize field values from deployment data
  React.useEffect(() => {
    if (hostingDeployment) {
      const initialValues = {
        entrypoint: hostingDeployment.entrypoint || '',
        watch_path: hostingDeployment.watch_path || '',
        user_callback_url: hostingDeployment.user_callback_url || ''
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

  const handleRedeploy = () => {
    // TODO: Implement redeploy functionality
    console.log('Redeploy triggered with changes:', fieldValues);
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
      </section>
      {/* Configuration Fields Section */}
      <section className="mb-8 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
        <h2 className="text-[16px] font-semibold text-[rgba(20,27,52,1)] mb-4">Configuration</h2>
        <div className="flex flex-col gap-4">
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
              className="px-6 py-3 bg-blue-600 text-white text-[14px] font-medium rounded-md hover:bg-blue-700 transition-colors"
              style={{
                animation: 'glowPulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
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
              Redeploy
            </button>
          </div>
        )}
      <section className="mb-8 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
        <h2 className="text-[16px] font-semibold text-[rgba(20,27,52,1)] mb-2">Configure Deploy Service</h2>
        <p className="text-[14px] text-[rgba(20,27,52,0.74)] mb-0">
          {hostingDeployment ? JSON.stringify(hostingDeployment, null, 2) : 'No deployment data'}
        </p>
        {/* Add configuration form or steps here */}
      </section>
        </>
      )}
    </div>
  );
}