"use client"
import React from 'react';
import { useParams } from 'next/navigation';
import { useDeployment, useDeployments } from '@/hooks/queries/useProjects';
import { IHostingProject } from '@/types/IProject';
import { GitHubLogoIcon } from '@radix-ui/react-icons';

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
  if (!isOpen) return null;
  return (
    <div className="absolute z-20 mt-2 w-96 max-h-80 overflow-y-auto bg-white border border-[rgba(222,224,244,1)] rounded shadow-lg p-2">
      {orgsWithRepos.length === 0 && (
        <div className="text-[14px] text-[rgba(230,90,126,1)]">No repositories found.</div>
      )}
      {orgsWithRepos.map((org) => (
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

// Editable Field Component
interface EditableFieldProps {
  label: string;
  value: string;
  placeholder: string;
  fieldKey: string;
  isEditing: boolean;
  onEdit: () => void;
  onSave: (value: string) => void;
  onCancel: () => void;
  onChange: (value: string) => void;
}

function EditableField({ 
  label, 
  value, 
  placeholder, 
  fieldKey, 
  isEditing, 
  onEdit, 
  onSave, 
  onCancel, 
  onChange 
}: EditableFieldProps) {
  const [localValue, setLocalValue] = React.useState(value);

  React.useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleSave = () => {
    onSave(localValue);
  };

  const handleCancel = () => {
    setLocalValue(value);
    onCancel();
  };

  return (
    <label className="text-[14px] text-[rgba(20,27,52,0.74)] mb-1 font-medium">
      {label}
      <div className="flex items-center gap-2 mt-1">
        <input 
          type="text" 
          placeholder={placeholder}
          value={localValue}
          onChange={(e) => setLocalValue(e.target.value)}
          readOnly={!isEditing}
          className={`flex-1 p-2 text-[14px] border rounded bg-white text-[rgba(20,27,52,1)] placeholder-[rgba(20,27,52,0.68)] transition-all ${
            isEditing 
              ? 'border-blue-400 ring-2 ring-blue-400 ring-opacity-50 shadow-lg focus:outline-none' 
              : 'border-[rgba(222,224,244,1)] focus:outline-none focus:ring-2 focus:ring-[rgba(20,27,52,0.68)] focus:border-[rgba(20,27,52,0.68)]'
          } ${!isEditing ? 'cursor-default' : ''}`}
        />
        <div className="flex items-center gap-1">
          {!isEditing ? (
            <button
              onClick={onEdit}
              className="w-8 h-8 flex items-center justify-center text-[rgba(20,27,52,0.5)] hover:text-[rgba(20,27,52,1)] hover:bg-[rgba(222,224,244,0.5)] rounded transition-colors"
              title="Edit"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10.293 1.293a1 1 0 0 1 1.414 0l1 1a1 1 0 0 1 0 1.414l-9 9A1 1 0 0 1 3 13H2a1 1 0 0 1-1-1v-1a1 1 0 0 1 .293-.707l9-9zM3 11h1l8-8-1-1-8 8v1z" fill="currentColor"/>
              </svg>
            </button>
          ) : (
            <>
              <button
                onClick={handleSave}
                className="w-8 h-8 flex items-center justify-center text-green-600 hover:text-green-700 hover:bg-green-50 rounded transition-colors"
                title="Save"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 4L5.5 10.5L2 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
              <button
                onClick={handleCancel}
                className="w-8 h-8 flex items-center justify-center text-[rgba(230,90,126,1)] hover:text-[rgba(200,60,96,1)] hover:bg-[rgba(230,90,126,0.1)] rounded transition-colors"
                title="Cancel"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M1 1L13 13M1 13L13 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </button>
            </>
          )}
        </div>
      </div>
    </label>
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
    agentProjectRoute: '',
    buildWatchPath: '',
    entrypoint: ''
  });

  // Helper to type-narrow deployment to IHostingProject
  const hostingDeployment = deployment as IHostingProject | undefined;

  // Initialize field values from deployment data
  React.useEffect(() => {
    if (hostingDeployment) {
      setFieldValues({
        agentProjectRoute: hostingDeployment.agentProjectRoute || '',
        buildWatchPath: hostingDeployment.buildWatchPath || '',
        entrypoint: hostingDeployment.entrypoint || ''
      });
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

  let content;
  if (isLoading) {
    content = <div className="text-[16px] font-['Figtree'] text-[rgba(20,27,52,0.74)]">Loading project...</div>;
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
            label="Agent Project Route"
            value={fieldValues.agentProjectRoute}
            placeholder="e.g. /src/agent"
            fieldKey="agentProjectRoute"
            isEditing={editingField === 'agentProjectRoute'}
            onEdit={() => handleFieldEdit('agentProjectRoute')}
            onSave={(value) => handleFieldSave('agentProjectRoute', value)}
            onCancel={handleFieldCancel}
            onChange={(value) => handleFieldChange('agentProjectRoute', value)}
          />
          <EditableField
            label="Build Watch Path"
            value={fieldValues.buildWatchPath}
            placeholder="e.g. /src"
            fieldKey="buildWatchPath"
            isEditing={editingField === 'buildWatchPath'}
            onEdit={() => handleFieldEdit('buildWatchPath')}
            onSave={(value) => handleFieldSave('buildWatchPath', value)}
            onCancel={handleFieldCancel}
            onChange={(value) => handleFieldChange('buildWatchPath', value)}
          />
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
        </div>
      </section>
      <section className="mb-8 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
        <h2 className="text-[16px] font-semibold text-[rgba(20,27,52,1)] mb-2">Configure Deploy Service</h2>
        <p className="text-[14px] text-[rgba(20,27,52,0.74)] mb-0">
          {hostingDeployment ? JSON.stringify(hostingDeployment, null, 2) : 'No deployment data'}
        </p>
        {/* Add configuration form or steps here */}
      </section>
    </div>
  );
}