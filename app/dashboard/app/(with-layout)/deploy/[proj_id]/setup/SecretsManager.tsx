"use client"
import React, { useState, useEffect } from 'react';
import { Alert01Icon as WarningIcon, Delete01Icon as TrashIcon } from 'hugeicons-react';

interface Secret {
  name: string;
}

interface SecretsManagerProps {
  projectId: string;
}

export default function SecretsManager({ projectId }: SecretsManagerProps) {
  const [activeTab, setActiveTab] = useState<'env' | 'individual'>('individual');
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [envContent, setEnvContent] = useState('');
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [secretToDelete, setSecretToDelete] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  // Load existing secrets
  const loadSecrets = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/deploy/deployments/${projectId}/secrets`, {
        method: 'GET',
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        setSecrets(data.secrets || []);
        
        // Convert secrets to .env format
        const envString = data.secrets?.map((secret: Secret) => `${secret.name}=`).join('\n') || '';
        setEnvContent(envString);
      } else {
        setError('Failed to load secrets');
      }
    } catch (err) {
      setError('Error loading secrets');
      console.error('Error loading secrets:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSecrets();
  }, [projectId]);

  // Save secret from .env format
  const saveEnvSecrets = async () => {
    setIsSaving(true);
    setError(null);
    
    try {
      const lines = envContent.split('\n').filter(line => line.trim());
      const secretsToSave = lines.map(line => {
        const [key, ...valueParts] = line.split('=');
        const value = valueParts.join('='); // Handle values that might contain '='
        return { name: key.trim(), value: value.trim() };
      }).filter(secret => secret.name && secret.value);

      // Save each secret
      for (const secret of secretsToSave) {
        const response = await fetch(`${apiUrl}/deploy/deployments/${projectId}/secrets`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify(secret),
        });
        
        if (!response.ok) {
          throw new Error(`Failed to save secret ${secret.name}`);
        }
      }
      
      // Reload secrets to update the list
      await loadSecrets();
    } catch (err) {
      setError('Error saving secrets');
      console.error('Error saving secrets:', err);
    } finally {
      setIsSaving(false);
    }
  };

  // Save individual secret
  const saveIndividualSecret = async () => {
    if (!newKey.trim() || !newValue.trim()) {
      setError('Both key and value are required');
      return;
    }

    setIsSaving(true);
    setError(null);
    
    try {
      const response = await fetch(`${apiUrl}/deploy/deployments/${projectId}/secrets`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          name: newKey.trim(),
          value: newValue.trim(),
        }),
      });
      
      if (response.ok) {
        setNewKey('');
        setNewValue('');
        await loadSecrets();
      } else {
        setError('Failed to save secret');
      }
    } catch (err) {
      setError('Error saving secret');
      console.error('Error saving secret:', err);
    } finally {
      setIsSaving(false);
    }
  };

  // Handle delete button click
  const handleDeleteClick = (secretName: string) => {
    setSecretToDelete(secretName);
    setShowDeleteModal(true);
  };

  // Confirm delete
  const confirmDelete = async () => {
    if (!secretToDelete) return;
    
    setIsDeleting(secretToDelete);
    setError(null);
    
    try {
      const response = await fetch(`${apiUrl}/deploy/deployments/${projectId}/secrets/${encodeURIComponent(secretToDelete)}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      
      if (response.ok) {
        await loadSecrets();
        setShowDeleteModal(false);
        setSecretToDelete(null);
      } else {
        setError(`Failed to delete secret ${secretToDelete}`);
      }
    } catch (err) {
      setError(`Error deleting secret ${secretToDelete}`);
      console.error('Error deleting secret:', err);
    } finally {
      setIsDeleting(null);
    }
  };

  // Cancel delete
  const cancelDelete = () => {
    setShowDeleteModal(false);
    setSecretToDelete(null);
  };

  return (
    <div className="border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <WarningIcon className="w-5 h-5 text-[rgba(237,216,103,1)]" />
        <h2 className="text-[16px] font-semibold text-[rgba(20,27,52,1)]">Environment Variables</h2>
      </div>
      
      <p className="text-[14px] text-[rgba(20,27,52,0.74)] mb-4">
        Manage environment variables and secrets for your deployment. These will be securely stored and made available to your application.
      </p>

      {/* Tab Navigation */}
      <div className="flex border-b border-[rgba(222,224,244,1)] mb-4">
        <button
          onClick={() => setActiveTab('env')}
          className={`px-4 py-2 text-[14px] font-medium transition-colors ${
            activeTab === 'env'
              ? 'text-[rgba(20,27,52,1)] border-b-2 border-[rgba(20,27,52,1)]'
              : 'text-[rgba(20,27,52,0.74)] hover:text-[rgba(20,27,52,1)]'
          }`}
        >
          .env Format
        </button>
        <button
          onClick={() => setActiveTab('individual')}
          className={`px-4 py-2 text-[14px] font-medium transition-colors ${
            activeTab === 'individual'
              ? 'text-[rgba(20,27,52,1)] border-b-2 border-[rgba(20,27,52,1)]'
              : 'text-[rgba(20,27,52,0.74)] hover:text-[rgba(20,27,52,1)]'
          }`}
        >
          Individual Keys
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-[rgba(230,90,126,0.1)] border border-[rgba(230,90,126,0.3)] rounded-md">
          <p className="text-[14px] text-[rgba(230,90,126,1)]">{error}</p>
        </div>
      )}

      {/* .env Format Tab */}
      {activeTab === 'env' && (
        <div>
          <div className="mb-4">
            <label className="block text-[14px] font-medium text-[rgba(20,27,52,1)] mb-2">
              Environment Variables (.env format)
            </label>
            <textarea
              value={envContent}
              onChange={(e) => setEnvContent(e.target.value)}
              placeholder="DATABASE_URL=postgresql://user:pass@localhost/db&#10;API_KEY=your_api_key_here&#10;SECRET_TOKEN=your_secret_token"
              className="w-full h-48 px-3 py-2 border border-[rgba(222,224,244,1)] rounded-md text-[14px] font-['Menlo'] focus:outline-none focus:ring-2 focus:ring-[rgba(20,27,52,0.2)] focus:border-[rgba(20,27,52,1)] resize-none"
            />
            <p className="text-[12px] text-[rgba(20,27,52,0.6)] mt-1">
              Enter environment variables in KEY=value format, one per line
            </p>
          </div>
          <button
            onClick={saveEnvSecrets}
            disabled={isSaving || isLoading}
            className="px-4 py-2 bg-[rgba(20,27,52,1)] text-white text-[14px] font-medium rounded-md hover:bg-[rgba(20,27,52,0.9)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? 'Saving...' : 'Save Environment Variables'}
          </button>
        </div>
      )}

      {/* Individual Keys Tab */}
      {activeTab === 'individual' && (
        <div>
          <div className="mb-4">
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-[14px] font-medium text-[rgba(20,27,52,1)] mb-2">
                  Key
                </label>
                <input
                  type="text"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  placeholder="e.g. DATABASE_URL"
                  className="w-full px-3 py-2 border border-[rgba(222,224,244,1)] rounded-md text-[14px] focus:outline-none focus:ring-2 focus:ring-[rgba(20,27,52,0.2)] focus:border-[rgba(20,27,52,1)]"
                />
              </div>
              <div>
                <label className="block text-[14px] font-medium text-[rgba(20,27,52,1)] mb-2">
                  Value
                </label>
                <input
                  type="password"
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  placeholder="e.g. postgresql://user:pass@localhost/db"
                  className="w-full px-3 py-2 border border-[rgba(222,224,244,1)] rounded-md text-[14px] focus:outline-none focus:ring-2 focus:ring-[rgba(20,27,52,0.2)] focus:border-[rgba(20,27,52,1)]"
                />
              </div>
            </div>
            <button
              onClick={saveIndividualSecret}
              disabled={isSaving || isLoading || !newKey.trim() || !newValue.trim()}
              className="px-4 py-2 bg-[rgba(20,27,52,1)] text-white text-[14px] font-medium rounded-md hover:bg-[rgba(20,27,52,0.9)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? 'Saving...' : 'Add Secret'}
            </button>
          </div>
        </div>
      )}

      {/* Existing Secrets List */}
      <div className="mt-6">
        <h3 className="text-[14px] font-semibold text-[rgba(20,27,52,1)] mb-3">Existing Secrets</h3>
        {isLoading ? (
          <div className="text-[14px] text-[rgba(20,27,52,0.74)]">Loading secrets...</div>
        ) : secrets.length > 0 ? (
          <div className="space-y-2">
            {secrets.map((secret, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-[rgba(248,249,250,1)] border border-[rgba(222,224,244,1)] rounded-md"
              >
                <div className="flex items-center gap-3">
                  <span className="text-[14px] font-['Menlo'] text-[rgba(20,27,52,1)]">
                    {secret.name}
                  </span>
                  <span className="text-[12px] text-[rgba(20,27,52,0.6)]">
                    ••••••••
                  </span>
                </div>
                <button
                  onClick={() => handleDeleteClick(secret.name)}
                  disabled={isDeleting === secret.name}
                  className="w-6 h-6 flex items-center justify-center text-[rgba(20,27,52,0.5)] hover:text-[rgba(230,90,126,1)] hover:bg-[rgba(230,90,126,0.1)] rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title={`Delete ${secret.name}`}
                >
                  <TrashIcon className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[14px] text-[rgba(20,27,52,0.74)] italic">
            No secrets configured yet
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
          <div className="bg-white rounded-lg shadow-lg p-6 min-w-[400px] max-w-[90vw]">
            <div className="mb-6">
              <div className="text-[16px] font-semibold mb-2 text-[rgba(230,90,126,1)]">Delete Secret</div>
              <div className="text-[14px] text-[rgba(20,27,52,0.74)] mb-4">
                Are you sure you want to delete the secret <strong>{secretToDelete}</strong>? This action cannot be undone.
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                className="px-4 py-2 rounded border border-[rgba(222,224,244,1)] bg-white text-[14px] font-medium hover:bg-[rgba(248,249,250,1)] transition-colors"
                onClick={cancelDelete}
                disabled={isDeleting === secretToDelete}
              >
                Cancel
              </button>
              <button
                className="px-4 py-2 rounded bg-[rgba(230,90,126,1)] text-white text-[14px] font-medium hover:bg-[rgba(200,60,96,1)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                onClick={confirmDelete}
                disabled={isDeleting === secretToDelete}
              >
                <TrashIcon className="w-4 h-4" />
                {isDeleting === secretToDelete ? 'Deleting...' : 'Delete Secret'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 