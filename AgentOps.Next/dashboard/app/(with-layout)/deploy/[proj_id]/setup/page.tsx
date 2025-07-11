"use client"
import React from 'react';
import { useParams } from 'next/navigation';
import { useProject } from '@/hooks/queries/useProjects';

function ProjectDetails({ projectId }: { projectId: string }) {
  const { project } = useProject(projectId);

  if (!project) {
    return <div className="text-red-500 dark:text-red-400">Project not found.</div>;
  }

  return (
    <div className="font-['Figtree'] text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700 rounded-lg p-6 mb-6 bg-white dark:bg-gray-800">
      <h1 className="text-[32px] mb-2 font-bold">{project.name}</h1>
      <div className="text-gray-600 dark:text-gray-400 text-[14px] mb-2">
        <strong className="text-gray-900 dark:text-white">Environment:</strong> {project.environment}
      </div>
      <div className="text-gray-600 dark:text-gray-400 text-[14px] mb-2">
        <strong className="text-gray-900 dark:text-white">API Key:</strong> <span className="font-['Menlo'] bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white px-1.5 py-0.5 rounded">{project.api_key}</span>
      </div>
      <div className="text-gray-600 dark:text-gray-400 text-[14px] mb-2">
        <strong className="text-gray-900 dark:text-white">Organization:</strong> {project.org?.name}
      </div>
      <div className="text-gray-600 dark:text-gray-400 text-[14px]">
        <strong className="text-gray-900 dark:text-white">Trace Count:</strong> {project.trace_count}
      </div>
    </div>
  );
}

export default function DeployProjectSetupPage() {
  const params = useParams();
  const proj_id = params.proj_id as string;

  return (
    <div className="font-['Figtree'] text-gray-900 dark:text-white">
      <ProjectDetails projectId={proj_id} />

      {/* Source Code Section */}
      <section className="mb-8">
        <h2 className="text-[16px] font-semibold text-gray-900 dark:text-white mb-3">Source Code</h2>
        <button className="font-['Figtree'] text-[14px] px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-600 rounded-md cursor-pointer font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
          Select GitHub repository
        </button>
      </section>

      {/* Configuration Fields Section */}
      <section className="mb-8">
        <h2 className="text-[16px] font-semibold text-gray-900 dark:text-white mb-3">Configuration</h2>
        <div className="flex flex-col gap-4">
          <label className="text-[14px] text-gray-600 dark:text-gray-400 mb-1">
            Agent Project Route
            <input 
              type="text" 
              placeholder="e.g. /src/agent" 
              className="block w-full mt-1 p-2 text-[14px] border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 dark:focus:ring-gray-400 focus:border-gray-500 dark:focus:border-gray-400" 
            />
          </label>
          <label className="text-[14px] text-gray-600 dark:text-gray-400 mb-1">
            Build Watch Path
            <input 
              type="text" 
              placeholder="e.g. /src" 
              className="block w-full mt-1 p-2 text-[14px] border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 dark:focus:ring-gray-400 focus:border-gray-500 dark:focus:border-gray-400" 
            />
          </label>
          <label className="text-[14px] text-gray-600 dark:text-gray-400 mb-1">
            Entrypoint
            <input 
              type="text" 
              placeholder="e.g. main.py" 
              className="block w-full mt-1 p-2 text-[14px] border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 dark:focus:ring-gray-400 focus:border-gray-500 dark:focus:border-gray-400" 
            />
          </label>
        </div>
      </section>

      <h1 className="text-gray-900 dark:text-white">Configure Deploy Service</h1>
      <p className="text-gray-600 dark:text-gray-400">Project ID: {proj_id}</p>
      {/* Add configuration form or steps here */}
    </div>
  );
}