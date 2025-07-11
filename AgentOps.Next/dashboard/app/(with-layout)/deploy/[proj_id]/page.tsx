"use client"
import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useProject, useDeployments } from '@/hooks/queries/useProjects';
import { Key01Icon } from 'hugeicons-react';
import { PlayIcon } from 'hugeicons-react';
import { useState } from 'react';

export default function DeployProjectPage() {
  const params = useParams();
  const router = useRouter();
  const proj_id = params.proj_id as string;

  const { project } = useProject(proj_id);
  const { data: deployments, isLoading: deploymentsLoading } = useDeployments();

  // Find the deployment for this project
  const deployment = deployments?.find((d) => d.id === proj_id);

  useEffect(() => {
    if (!deploymentsLoading && !deployment) {
      router.replace('/deploy');
    }
  }, [deploymentsLoading, deployment, router]);

  if (deploymentsLoading) {
    return <div className="text-gray-900 dark:text-white">Loading...</div>;
  }

  if (!deployment) {
    // Redirect will happen, but render nothing
    return null;
  }

  const [showTooltip, setShowTooltip] = useState(false);
  const [copied, setCopied] = useState(false);
  const [jsonInput, setJsonInput] = useState('{"input":{}}');

  const handleCopy = () => {
    if (project?.api_key) {
      navigator.clipboard.writeText(project.api_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    }
  };

  const handleRunAgent = () => {
    // TODO: Implement actual functionality
    console.log('Running agent with input:', jsonInput);
  };

  return (
    <div className="relative font-['Figtree'] text-gray-900 dark:text-white mx-8">
      <button
        className="absolute top-5 right-5 flex items-center justify-center p-2 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors z-10"
        onClick={handleCopy}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        aria-label="Copy API Key"
        type="button"
      >
        <Key01Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        {(showTooltip || copied) && (
          <span className={`absolute z-10 top-12 right-0 whitespace-nowrap rounded bg-gray-900 dark:bg-gray-100 px-2 py-1 text-xs text-white dark:text-gray-900 shadow transition-opacity ${copied ? 'opacity-100' : 'opacity-90'}`}>
            {copied ? 'Copied!' : 'copy api key'}
          </span>
        )}
      </button>

      <h1 className="text-[32px] font-bold mt-5 mb-1">{project?.name}</h1>
      <div className="text-[24px] text-gray-600 dark:text-gray-400 mb-10">
        {project?.org?.name}
      </div>

      <div className="flex gap-6">
        <div className="flex-1 w-2/3">
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6 mb-6 bg-white dark:bg-gray-800">
            <h2 className="text-[16px] font-semibold text-gray-900 dark:text-white mb-3">Project Details</h2>
            <div className="text-[14px] text-gray-600 dark:text-gray-400 mb-2">
              <strong className="text-gray-900 dark:text-white">Name:</strong> {project?.name}
            </div>
            <div className="text-[14px] text-gray-600 dark:text-gray-400 mb-2">
              <strong className="text-gray-900 dark:text-white">Environment:</strong> {project?.environment}
            </div>
            <div className="text-[14px] text-gray-600 dark:text-gray-400 mb-2">
              <strong className="text-gray-900 dark:text-white">API Key:</strong> <span className="font-['Menlo'] bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white px-2 py-0.5 rounded">{project?.api_key}</span>
            </div>
            <div className="text-[14px] text-gray-600 dark:text-gray-400 mb-2">
              <strong className="text-gray-900 dark:text-white">Organization:</strong> {project?.org?.name}
            </div>
            <div className="text-[14px] text-gray-600 dark:text-gray-400">
              <strong className="text-gray-900 dark:text-white">Trace Count:</strong> {project?.trace_count}
            </div>
          </div>
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6 bg-white dark:bg-gray-800">
            <h2 className="text-[16px] font-semibold text-gray-900 dark:text-white mb-3">Deployment Details</h2>
            <div className="text-[14px] text-gray-600 dark:text-gray-400 mb-2">
              <strong className="text-gray-900 dark:text-white">Deployment ID:</strong> {deployment.id}
            </div>
          </div>
        </div>

        <div className="flex-none w-1/3">
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6 bg-white dark:bg-gray-800">
            <div className="flex items-center gap-2 mb-4">
              <PlayIcon className="w-6 h-6 text-gray-600 dark:text-gray-400" />
              <h2 className="text-[20px] font-semibold text-gray-900 dark:text-white">Run Your Agent</h2>
            </div>
            <div className="mb-4">
              <label className="block text-[14px] font-medium text-gray-900 dark:text-white mb-2">
                Endpoint
              </label>
              <div className="border border-gray-200 dark:border-gray-700 rounded bg-gray-50 dark:bg-gray-700 p-3">
                <div className="font-['Menlo'] text-[13px] text-gray-600 dark:text-gray-400">
                  POST http://api.agentops.ai/deploy/{proj_id}/run
                </div>
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-[14px] font-medium text-gray-900 dark:text-white mb-2">
                Request Body
              </label>
              <textarea
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                className="w-full h-32 p-3 border border-gray-200 dark:border-gray-700 rounded font-['Menlo'] text-[13px] text-gray-900 dark:text-white bg-white dark:bg-gray-800 resize-none focus:outline-none focus:ring-2 focus:ring-gray-500 dark:focus:ring-gray-400 focus:border-gray-500 dark:focus:border-gray-400"
                placeholder='{"input":{}}'
              />
            </div>
            {/* Run Agent and Docs Buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleRunAgent}
                className="flex-1 bg-gray-900 dark:bg-white text-white dark:text-gray-900 px-4 py-2 rounded font-medium text-[14px] hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 dark:focus:ring-gray-400"
                type="button"
              >
                Run Agent
              </button>
              <button
                className="flex-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white px-4 py-2 rounded font-medium text-[14px] hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 dark:focus:ring-gray-400"
                type="button"
              >
                Docs
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}