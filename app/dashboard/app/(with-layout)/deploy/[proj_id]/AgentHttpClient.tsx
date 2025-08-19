import React, { useState, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import { PlayIcon } from 'hugeicons-react';

// Dynamically import Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-32 border border-[rgba(222,224,244,1)] rounded bg-[rgba(248,249,250,1)] flex items-center justify-center">
      <div className="text-[rgba(20,27,52,0.74)] text-[14px]">Loading editor...</div>
    </div>
  ),
});

interface AgentHttpClientProps {
  proj_id: string;
  api_key?: string;
}

interface JobStatus {
  job_id: string;
  status: string;
  message: string;
  timestamp: string;
}

const AgentHttpClient: React.FC<AgentHttpClientProps> = ({ proj_id }) => {
  const [jsonInput, setJsonInput] = useState('{"inputs":{}}');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [currentJob, setCurrentJob] = useState<JobStatus | null>(null);
  const [jobEvents, setJobEvents] = useState<JobStatus[]>([]);
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const startPolling = (jobId: string) => {
    setIsPolling(true);
    setJobEvents([]);
    
    // Poll every 2 seconds
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
        if (!apiUrl) {
          throw new Error('NEXT_PUBLIC_API_URL is not set');
        }
        const response = await fetch(`${apiUrl}/deploy/deployments/${proj_id}/jobs/${jobId}/status`, {
          credentials: 'include',
        });

        if (!response.ok) {
          // Stop polling and report error
          stopPolling();
          setError(`Failed to fetch job status: HTTP ${response.status}`);
          return;
        }

        const data = await response.json();
        const events = data.events || [];
        
        setJobEvents(events);
        
        // Update current job status with the latest event
        if (events.length > 0) {
          const latestEvent = events[0];
          setCurrentJob({
            job_id: jobId,
            status: latestEvent.status,
            message: latestEvent.message,
            timestamp: latestEvent.timestamp,
          });

          // Stop polling if job is completed or failed
          if (["completed", "failed", "error"].includes(latestEvent.status.toLowerCase())) {
            stopPolling();
          }
        }
      } catch (error) {
        // Stop polling and report error
        stopPolling();
        const errorMessage = error instanceof Error ? error.message : 'An error occurred while polling job status';
        setError(errorMessage);
        console.error('Error polling job status:', error);
      }
    }, 2000);
  };

  const stopPolling = () => {
    setIsPolling(false);
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  };

  const getStatusColor = (status: string) => {
    const statusLower = status.toLowerCase();
    if (['completed', 'success'].includes(statusLower)) return 'text-green-600';
    if (['failed', 'error'].includes(statusLower)) return 'text-red-600';
    if (['running', 'processing'].includes(statusLower)) return 'text-blue-600';
    if (['queued', 'pending'].includes(statusLower)) return 'text-yellow-600';
    return 'text-gray-600';
  };

  const getStatusIcon = (status: string) => {
    const statusLower = status.toLowerCase();
    if (['completed', 'success'].includes(statusLower)) return '✅';
    if (['failed', 'error'].includes(statusLower)) return '❌';
    if (['running', 'processing'].includes(statusLower)) return '🔄';
    if (['queued', 'pending'].includes(statusLower)) return '⏳';
    return '📋';
  };

  const handleRunAgent = async () => {
    if (!validateJson(jsonInput)) {
      setError('Invalid JSON format');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccess(null);
    setCurrentJob(null);
    setJobEvents([]);
    stopPolling();

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        throw new Error('NEXT_PUBLIC_API_URL is not set');
      }
      const response = await fetch(`${apiUrl}/deploy/deployments/${proj_id}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonInput,
        credentials: 'include', // This includes the session cookie
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setSuccess(`Job queued successfully! Job ID: ${result.job_id}`);
      console.log('Job queued:', result.job_id);
      
      // Start polling for job updates
      startPolling(result.job_id);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred while running the agent';
      setError(errorMessage);
      console.error('Error running agent:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditorChange = (value: string | undefined) => {
    setJsonInput(value || '{"inputs":{}}');
    // Clear previous error/success messages when user starts typing
    if (error || success) {
      setError(null);
      setSuccess(null);
    }
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
          <div className="font-['Menlo'] text-[13px] text-gray-600 dark:text-gray-400 break-all">
            POST /deploy/deployments/{proj_id}/run
          </div>
        </div>
      </div>
      <div className="mb-4">
        <label className="block text-[14px] font-medium text-gray-900 dark:text-white mb-2">
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
      
      {/* Status Messages */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-[14px]">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-green-700 text-[14px]">
          {success}
        </div>
      )}

      {/* Job Status Display */}
      {currentJob && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">{getStatusIcon(currentJob.status)}</span>
            <h3 className="text-[16px] font-medium text-gray-900">Job Status</h3>
            {isPolling && (
              <div className="flex items-center gap-1 text-blue-600 text-[12px]">
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
                Live
              </div>
            )}
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-[14px] font-medium text-gray-700">Status:</span>
              <span className={`text-[14px] font-medium ${getStatusColor(currentJob.status)}`}>
                {currentJob.status}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[14px] font-medium text-gray-700">Job ID:</span>
              <span className="text-[14px] font-['Menlo'] text-gray-600">{currentJob.job_id}</span>
            </div>
            {currentJob.message && (
              <div className="flex items-start gap-2">
                <span className="text-[14px] font-medium text-gray-700">Message:</span>
                <span className="text-[14px] text-gray-600">{currentJob.message}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Job Events History */}
      {jobEvents.length > 0 && (
        <div className="mb-4">
          <h3 className="text-[16px] font-medium text-gray-900 mb-2">Job Events</h3>
          <div className="max-h-48 overflow-y-auto border border-gray-200 rounded">
            {jobEvents.map((event, index) => (
              <div key={index} className="p-3 border-b border-gray-100 last:border-b-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm">{getStatusIcon(event.status)}</span>
                  <span className={`text-[14px] font-medium ${getStatusColor(event.status)}`}>
                    {event.status}
                  </span>
                  <span className="text-[12px] text-gray-500">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                {event.message && (
                  <p className="text-[13px] text-gray-600 ml-6">{event.message}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Run Agent and Docs Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleRunAgent}
          disabled={isLoading || !validateJson(jsonInput) || isPolling}
          className="flex-1 bg-[rgba(20,27,52,1)] text-white px-4 py-2 rounded font-medium text-[14px] hover:bg-[rgba(20,27,52,0.85)] transition-colors focus:outline-none focus:ring-2 focus:ring-[rgba(20,27,52,0.2)] disabled:opacity-50 disabled:cursor-not-allowed"
          type="button"
        >
          {isLoading ? 'Running...' : isPolling ? 'Job Running...' : 'Run Agent'}
        </button>
        <button
          className="flex-1 bg-white border border-[rgba(222,224,244,1)] text-[rgba(20,27,52,1)] px-4 py-2 rounded font-medium text-[14px] hover:bg-[rgba(222,224,244,0.5)] transition-colors focus:outline-none focus:ring-2 focus:ring-[rgba(20,27,52,0.2)]"
          type="button"
        >
          Docs
        </button>
      </div>
    </div>
  );
};

export default AgentHttpClient; 