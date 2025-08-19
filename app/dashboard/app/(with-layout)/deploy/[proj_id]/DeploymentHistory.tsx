import React from 'react';
import { ArrowDown01Icon as ChevronDownIcon, MoreHorizontalIcon as MoreVerticalIcon, CheckmarkCircle01Icon as CheckIcon, StarIcon, Globe02Icon as GlobeIcon, MapPinIcon, CloudServerIcon as ServerIcon } from 'hugeicons-react';
import { useDeploymentHistory } from '@/hooks/queries/useProjects';

interface DeploymentHistoryProps {
  projectId: string;
}

const DeploymentHistory: React.FC<DeploymentHistoryProps> = ({ projectId }) => {
  const { data: historyData, isLoading, error } = useDeploymentHistory(projectId);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
      case 'running':
      case 'success':
        return 'bg-green-600 text-white';
      case 'failed':
      case 'error':
        return 'bg-red-600 text-white';
      case 'pending':
      case 'queued':
        return 'bg-yellow-600 text-white';
      case 'skipped':
      case 'cancelled':
        return 'bg-gray-500 text-white';
      default:
        return 'bg-gray-500 text-white';
    }
  };

  const getStatusDisplay = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
      case 'running':
        return 'RUNNING';
      case 'success':
        return 'SUCCESS';
      case 'failed':
      case 'error':
        return 'FAILED';
      case 'pending':
      case 'queued':
        return 'PENDING';
      case 'skipped':
        return 'SKIPPED';
      case 'cancelled':
        return 'CANCELLED';
      default:
        return status.toUpperCase();
    }
  };

  if (isLoading) {
    return (
      <div className="mt-8">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="h-6 w-40 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg animate-pulse">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 bg-gray-200 dark:bg-gray-600 rounded-full"></div>
                    <div className="h-4 w-32 bg-gray-200 dark:bg-gray-600 rounded"></div>
                  </div>
                  <div className="h-4 w-20 bg-gray-200 dark:bg-gray-600 rounded"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-8">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-[16px] font-semibold text-gray-900 dark:text-white">Deployment History</h2>
          </div>
          <div className="p-6">
            <div className="text-center text-gray-600 dark:text-gray-400">
              Failed to load deployment history. Please try again later.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const jobs = historyData?.jobs || [];
  const currentJob = jobs.find(job => job.status.toLowerCase() === 'running' || job.status.toLowerCase() === 'active');
  const historicalJobs = jobs.filter(job => job.status.toLowerCase() !== 'running' && job.status.toLowerCase() !== 'active');

  return (
    <div className="mt-8">
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm">
        {/* Card Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-[16px] font-semibold text-gray-900 dark:text-white">Deployment History</h2>
        </div>

        {/* Card Content */}
        <div className="p-6">
          {/* Information Banner */}
          {/* <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700/30 rounded-lg">
            <div className="flex items-center gap-2">
              <StarIcon className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
              <span className="text-[14px] text-yellow-800 dark:text-yellow-200">
                The deployment configuration was automatically modified to ignore deprecated regions.{' '}
                <button className="text-yellow-700 dark:text-yellow-300 underline hover:text-yellow-800 dark:hover:text-yellow-100 font-medium">
                  View details
                </button>
              </span>
            </div>
          </div> */}

          {/* Current Deployment Section */}
          {currentJob && (
            <div className="mb-6">
              <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700/50 rounded-lg p-4 relative">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(currentJob.status)}`}>
                      {getStatusDisplay(currentJob.status)}
                    </span>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-gray-600 dark:bg-gray-600 rounded-full flex items-center justify-center">
                        <span className="text-xs text-white font-medium">JD</span>
                      </div>
                      <div className="w-5 h-5 bg-gray-700 dark:bg-gray-700 rounded flex items-center justify-center">
                        <span className="text-xs text-gray-300">🐙</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded transition-colors font-medium">
                      View logs
                    </button>
                    <button className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors">
                      <MoreVerticalIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                    </button>
                  </div>
                </div>
                
                <div className="mb-3">
                  <p className="text-[14px] text-gray-900 dark:text-gray-200 mb-1 font-medium">
                    {currentJob.message || 'Deployment in progress'}
                  </p>
                  <p className="text-[12px] text-gray-600 dark:text-gray-400">
                    {new Date(currentJob.queued_at).toLocaleString()} via GitHub
                  </p>
                </div>

                {currentJob.status.toLowerCase() === 'success' && (
                  <div className="flex items-center gap-2">
                    <CheckIcon className="w-4 h-4 text-green-600 dark:text-green-400" />
                    <span className="text-[14px] text-green-700 dark:text-green-400 font-medium">Deployment successful</span>
                  </div>
                )}

                <button className="absolute bottom-2 right-2 p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors">
                  <ChevronDownIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                </button>
              </div>
            </div>
          )}

          {/* History Section */}
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-3">
              <h3 className="text-[14px] font-semibold text-gray-900 dark:text-gray-200">HISTORY</h3>
              <ChevronDownIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </div>
            
            {historicalJobs.length === 0 ? (
              <div className="text-center text-gray-600 dark:text-gray-400 py-8">
                No deployment history available
              </div>
            ) : (
              <div className="space-y-2">
                {historicalJobs.map((job) => (
                  <div
                    key={job.id}
                    className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(job.status)}`}>
                          {getStatusDisplay(job.status)}
                        </span>
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-gray-600 dark:bg-gray-600 rounded-full flex items-center justify-center">
                            <span className="text-xs text-white font-medium">JD</span>
                          </div>
                          <div className="w-5 h-5 bg-gray-700 dark:bg-gray-700 rounded flex items-center justify-center">
                            <span className="text-xs text-gray-300">🐙</span>
                          </div>
                        </div>
                      </div>
                      <button className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors">
                        <MoreVerticalIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                      </button>
                    </div>
                    
                    <div className="mt-3">
                      <p className="text-[14px] text-gray-900 dark:text-gray-200 mb-1 font-medium">
                        {job.message || 'Deployment job'}
                      </p>
                      <p className="text-[12px] text-gray-600 dark:text-gray-400">
                        {new Date(job.queued_at).toLocaleString()} via GitHub
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeploymentHistory; 