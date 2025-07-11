"use client"
import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useProject, useDeployments } from '@/hooks/queries/useProjects';
import { Key01Icon } from 'hugeicons-react';
import { PlayIcon } from 'hugeicons-react';
import { useState } from 'react';
import dynamic from 'next/dynamic';
import HostingMetrics from './HostingMetrics';
import AgentHttpClient from './AgentHttpClient';
import { Settings01Icon } from 'hugeicons-react'; // Add this import
import Link from 'next/link'; // Add this import

// Dynamically import Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-32 border border-gray-300 dark:border-gray-600 rounded bg-gray-50 dark:bg-gray-800 flex items-center justify-center">
      <div className="text-gray-700 dark:text-gray-300 text-[14px]">Loading editor...</div>
    </div>
  ),
});

export default function DeployProjectPage() {
  const params = useParams();
  const router = useRouter();
  const proj_id = params.proj_id as string;

  const { project } = useProject(proj_id);
  const { data: deployments, isLoading: deploymentsLoading } = useDeployments();

  const deployment = deployments?.find((d) => d.id === proj_id);

  const [showTooltip, setShowTooltip] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!deploymentsLoading && !deployment) {
      router.replace('/deploy');
    }
  }, [deploymentsLoading, deployment, router]);

  if (deploymentsLoading) {
    return <div className="text-gray-900 dark:text-white">Loading...</div>;
  }

  if (!deployment) {
    router.replace('/deploy');
    return null;
  }

  const handleCopy = () => {
    if (project?.api_key) {
      navigator.clipboard.writeText(project.api_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    }
  };

  return (
    <div className="relative font-['Figtree'] text-gray-900 dark:text-white mx-8">
      <style jsx>{`
        @keyframes fadeInOut {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        
        /* Ensure the animation works well in both light and dark modes */
        .pulse-animation {
          animation: fadeInOut 2.5s ease-in-out infinite;
        }
        
        /* Dark mode specific adjustments for animations if needed */
        .dark .pulse-animation {
          /* Could add dark-specific animation tweaks here if needed */
        }
      `}</style>
      <div className="absolute top-5 right-5 flex items-center gap-2 z-10">
        <button
          className="flex items-center justify-center p-2 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          onClick={handleCopy}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          aria-label="Copy API Key"
          type="button"
        >
          <Key01Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          {(showTooltip || copied) && (
            <span className={`absolute z-10 top-12 right-0 whitespace-nowrap rounded bg-gray-900 dark:bg-gray-700 px-2 py-1 text-xs text-white dark:text-gray-200 shadow-lg border border-gray-600 dark:border-gray-500 transition-opacity ${copied ? 'opacity-100' : 'opacity-90'}`}>
              {copied ? 'Copied!' : 'copy api key'}
            </span>
          )}
        </button>
        <Link href={`/deploy/${proj_id}/setup`} passHref legacyBehavior>
          <a
            className="flex items-center justify-center p-2 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            aria-label="Project Settings"
          >
            <Settings01Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </a>
        </Link>
      </div>

      <div className="flex items-center gap-3 mt-5 mb-1">
        <h1 className="text-[32px] font-bold text-gray-900 dark:text-white">{project?.name}</h1>
        <span className="flex items-center gap-1 ml-3">
          <span 
            className="inline-block w-3 h-3 rounded-full pulse-animation bg-green-500 dark:bg-green-400" 
            aria-label="Running"
          />
          <span className="text-[16px] font-medium text-green-600 dark:text-green-400">Running</span>
        </span>
      </div>
      <div className="text-[24px] text-gray-600 dark:text-gray-400 mb-10">
        {project?.org?.name} Organization
      </div>

      <div className="flex gap-6">
        <div className="flex-1 w-2/3">
          <div className="mt-0">
            <HostingMetrics />
          </div>
        </div>

        <div className="flex-none w-1/3">
          <AgentHttpClient proj_id={proj_id} api_key={project?.api_key} />
        </div>
      </div>
    </div>
  );
}