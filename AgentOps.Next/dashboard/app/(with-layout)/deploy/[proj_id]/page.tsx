"use client"
import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useProject, useDeployments } from '@/hooks/queries/useProjects';
import { Key01Icon } from 'hugeicons-react';
import { PlayIcon } from 'hugeicons-react';
import { useState } from 'react';
import dynamic from 'next/dynamic';

// Dynamically import Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-32 border border-[rgba(222,224,244,1)] rounded bg-[rgba(248,249,250,1)] flex items-center justify-center">
      <div className="text-[rgba(20,27,52,0.74)] text-[14px]">Loading editor...</div>
    </div>
  ),
});

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
    return <div>Loading...</div>;
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

  const handleEditorChange = (value: string | undefined) => {
    setJsonInput(value || '{"input":{}}');
  };

  const validateJson = (jsonString: string) => {
    try {
      JSON.parse(jsonString);
      return true;
    } catch {
      return false;
    }
  };

  return (
    <div className="relative font-['Figtree'] text-[rgba(20,27,52,1)] mx-8">
      <button
        className="absolute top-5 right-5 flex items-center justify-center p-2 rounded border border-[rgba(222,224,244,1)] bg-white hover:bg-[rgba(222,224,244,0.5)] transition-colors z-10"
        onClick={handleCopy}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        aria-label="Copy API Key"
        type="button"
      >
        <Key01Icon className="w-5 h-5 text-[rgba(20,27,52,0.68)]" />
        {(showTooltip || copied) && (
          <span className={`absolute z-10 top-12 right-0 whitespace-nowrap rounded bg-[rgba(20,27,52,1)] px-2 py-1 text-xs text-white shadow transition-opacity ${copied ? 'opacity-100' : 'opacity-90'}`}>
            {copied ? 'Copied!' : 'copy api key'}
          </span>
        )}
      </button>

      <h1 className="text-[32px] font-bold mt-5 mb-1">{project?.name}</h1>
      <div className="text-[24px] text-[rgba(20,27,52,0.74)] mb-10">
        {project?.org?.name}
      </div>

      <div className="flex gap-6">
        <div className="flex-1 w-2/3">
          <div className="border border-[rgba(222,224,244,1)] rounded-lg p-6 mb-6">
            <h2 className="text-[16px] font-semibold text-[rgba(20,27,52,1)] mb-3">Project Details</h2>
            <div className="text-[14px] text-[rgba(20,27,52,0.74)] mb-2">
              <strong>Name:</strong> {project?.name}
            </div>
            <div className="text-[14px] text-[rgba(20,27,52,0.74)] mb-2">
              <strong>Environment:</strong> {project?.environment}
            </div>
            <div className="text-[14px] text-[rgba(20,27,52,0.74)] mb-2">
              <strong>API Key:</strong> <span className="font-['Menlo'] bg-[rgba(222,224,244,1)] px-2 py-0.5 rounded">{project?.api_key}</span>
            </div>
            <div className="text-[14px] text-[rgba(20,27,52,0.74)] mb-2">
              <strong>Organization:</strong> {project?.org?.name}
            </div>
            <div className="text-[14px] text-[rgba(20,27,52,0.74)]">
              <strong>Trace Count:</strong> {project?.trace_count}
            </div>
          </div>
          <div className="border border-[rgba(222,224,244,1)] rounded-lg p-6">
            <h2 className="text-[16px] font-semibold text-[rgba(20,27,52,1)] mb-3">Deployment Details</h2>
            <div className="text-[14px] text-[rgba(20,27,52,0.74)] mb-2">
              <strong>Deployment ID:</strong> {deployment.id}
            </div>
          </div>
        </div>

        <div className="flex-none w-1/3">
          <div className="border border-[rgba(222,224,244,1)] rounded-lg p-6 bg-white">
            <div className="flex items-center gap-2 mb-4">
              <PlayIcon className="w-6 h-6 text-[rgba(20,27,52,0.68)]" />
              <h2 className="text-[20px] font-semibold text-[rgba(20,27,52,1)]">Run Your Agent</h2>
            </div>
            <div className="mb-4">
              <label className="block text-[14px] font-medium text-[rgba(20,27,52,1)] mb-2">
                Endpoint
              </label>
              <div className="border border-[rgba(222,224,244,1)] rounded bg-[rgba(248,249,250,1)] p-3">
                <div className="font-['Menlo'] text-[13px] text-[rgba(20,27,52,0.74)]">
                  POST http://api.agentops.ai/deploy/{proj_id}/run
                </div>
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-[14px] font-medium text-[rgba(20,27,52,1)] mb-2">
                Request Body
              </label>
              <div className="border border-[rgba(222,224,244,1)] rounded overflow-hidden">
                <MonacoEditor
                  height="128px"
                  defaultLanguage="json"
                  value={jsonInput}
                  onChange={handleEditorChange}
                  theme="light"
                  options={{
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    fontSize: 13,
                    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
                    lineNumbers: 'off',
                    folding: false,
                    wordWrap: 'on',
                    automaticLayout: true,
                    padding: { top: 12, bottom: 12 },
                    bracketPairColorization: { enabled: true },
                    formatOnPaste: true,
                    formatOnType: true,
                    tabSize: 2,
                    insertSpaces: true,
                  }}
                />
              </div>
              {!validateJson(jsonInput) && (
                <div className="text-red-500 text-[12px] mt-1">
                  Invalid JSON format
                </div>
              )}
            </div>
            {/* Run Agent and Docs Buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleRunAgent}
                className="flex-1 bg-[rgba(20,27,52,1)] text-white px-4 py-2 rounded font-medium text-[14px] hover:bg-[rgba(20,27,52,0.85)] transition-colors focus:outline-none focus:ring-2 focus:ring-[rgba(20,27,52,0.2)]"
                type="button"
              >
                Run Agent
              </button>
              <button
                className="flex-1 bg-white border border-[rgba(222,224,244,1)] text-[rgba(20,27,52,1)] px-4 py-2 rounded font-medium text-[14px] hover:bg-[rgba(222,224,244,0.5)] transition-colors focus:outline-none focus:ring-2 focus:ring-[rgba(20,27,52,0.2)]"
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