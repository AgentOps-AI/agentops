"use client"
import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useDeployment } from '@/hooks/queries/useProjects';
import { Key01Icon, ArrowLeft01Icon } from 'hugeicons-react';
import { useState } from 'react';
import dynamic from 'next/dynamic';
import HostingMetrics from './HostingMetrics';
import AgentHttpClient from './AgentHttpClient';
import { Settings01Icon } from 'hugeicons-react';
import Link from 'next/link';
import DeploymentHistory from './DeploymentHistory';
import LoadingSkeleton from './LoadingSkeleton';

export default function DeployProjectPage() {
  const params = useParams();
  const router = useRouter();
  const proj_id = params.proj_id as string;

  const { deployment, isLoading: deploymentsLoading } = useDeployment(proj_id);

  const [showTooltip, setShowTooltip] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!deploymentsLoading && !deployment) {
      router.replace('/deploy');
    }
  }, [deploymentsLoading, deployment, router]);

  // Show loading skeleton while data is loading
  if (deploymentsLoading || !deployment) {
    return <LoadingSkeleton />;
  }

  const handleCopy = () => {
    if (deployment?.api_key) {
      navigator.clipboard.writeText(deployment.api_key);
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
      
      {/* Back Button */}
      <div className="mb-4">
        <button 
          onClick={() => router.push('/deploy')}
          className="flex items-center mt-6 gap-2 text-[14px] text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft01Icon className="w-4 h-4" />
          <span>View all agents</span>
        </button>
      </div>

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
        <h1 className="text-[32px] font-bold text-gray-900 dark:text-white">{deployment?.name}</h1>
        <span className="flex items-center gap-1 ml-3">
          <span 
            className="inline-block w-3 h-3 rounded-full pulse-animation bg-green-500 dark:bg-green-400" 
            aria-label="Running"
          />
          <span className="text-[16px] font-medium text-green-600 dark:text-green-400">Running</span>
        </span>
      </div>
      <div className="text-[24px] text-gray-600 dark:text-gray-400 mb-10">
        {deployment?.org?.name} Organization
      </div>

      <div className="flex gap-6">
        <div className="flex-1 w-2/3">
          <div className="mt-0">
            <HostingMetrics />
          </div>
        </div>

        <div className="flex-none w-1/3">
          <AgentHttpClient proj_id={proj_id} api_key={deployment?.api_key} />
        </div>
      </div>

      <DeploymentHistory projectId={proj_id} />
    </div>
  );
}