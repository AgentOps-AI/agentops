/* eslint-disable */
'use client';

import { Button } from '@/components/ui/button';
import React, { useEffect, useState } from 'react';
import { fetchAuthenticatedApi, ApiError } from '@/lib/api-client';
import { toast } from '@/components/ui/use-toast';
import { IUser } from '@/types/IUser';
import ResultsDisplay from './components/ResultsDisplay';
import ApiTestSection from './components/ApiTestSection';
import AuthSection, { LoginType } from './components/AuthSection';
import { notFound } from 'next/navigation';

const SimpleLoginPageProd = () => {
  notFound();
  return null;
};

const SimpleLoginPageDev = () => {
  const [authStatus, setAuthStatus] = useState<string>('Initializing...');
  const [isSignedIn, setIsSignedIn] = useState<boolean>(false);
  const [userFullName, setUserFullName] = useState<string | null>(null);
  const [selectedLoginType, setSelectedLoginType] = useState<LoginType>('google');
  const [loginMethodUsed, setLoginMethodUsed] = useState<LoginType | null>(null);

  const [projectsStatus, setProjectsStatus] = useState<string>('Idle');
  const [projectsData, setProjectsData] = useState<any>(null);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  const [metricsStatus, setMetricsStatus] = useState<string>('Needs Project ID');
  const [metricsData, setMetricsData] = useState<any>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);

  const [tracesStatus, setTracesStatus] = useState<string>('Needs Project ID');
  const [tracesData, setTracesData] = useState<any>(null);
  const [tracesError, setTracesError] = useState<string | null>(null);

  const [projectIdForV4, setProjectIdForV4] = useState<string | null>(null);

  const [placeholderStatus, setPlaceholderStatus] = useState<string>('Idle');
  const [placeholderData, setPlaceholderData] = useState<any>(null);
  const [placeholderError, setPlaceholderError] = useState<string | null>(null);

  const [traceDetailStatus, setTraceDetailStatus] = useState<string>(
    'Needs Project ID and Trace ID',
  );
  const [traceDetailData, setTraceDetailData] = useState<any>(null);
  const [traceDetailError, setTraceDetailError] = useState<string | null>(null);
  const [firstTraceIdForDisplay, setFirstTraceIdForDisplay] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const authBaseUrl = `${apiUrl}/auth`;

  const checkAuthAndFetchDetails = async () => {
    const lastLoginMethod = localStorage.getItem('loginMethodUsed') as LoginType | null;
    if (loginMethodUsed !== lastLoginMethod) {
      setLoginMethodUsed(lastLoginMethod);
    }

    try {
      const user = await fetchAuthenticatedApi<IUser>('/opsboard/users/me');
      if (user) {
        setUserFullName(user.full_name || 'Full Name Missing');
        setIsSignedIn(true);
        return true;
      } else {
        console.warn('fetchAuthenticatedApi returned null/undefined user unexpectedly.');
        setIsSignedIn(false);
        setUserFullName(null);
        localStorage.removeItem('loginMethodUsed');
        if (loginMethodUsed !== null) setLoginMethodUsed(null);
        return false;
      }
    } catch (error: any) {
      setIsSignedIn(false);
      setUserFullName(null);
      localStorage.removeItem('loginMethodUsed');
      if (loginMethodUsed !== null) setLoginMethodUsed(null);

      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        return false;
      } else if (
        error.name === 'AbortError' ||
        error.message?.includes('fetch aborted') ||
        error.message?.includes('cancelled') ||
        error.message?.includes('navigation')
      ) {
        return false;
      } else {
        throw error;
      }
    }
  };

  useEffect(() => {
    let isMounted = true;
    setAuthStatus('Checking session...');
    checkAuthAndFetchDetails()
      .then((signedIn) => {
        if (!isMounted) return;
        if (signedIn && userFullName) {
          const methodDisplay = loginMethodUsed ? ` via ${loginMethodUsed}` : '';
          setAuthStatus(`Signed in as: ${userFullName}${methodDisplay}`);
          if (projectsStatus === 'Idle') setProjectsStatus('Ready');
        } else {
          setAuthStatus('Not signed in.');
          setProjectsStatus('Idle');
          setMetricsStatus('Needs Project ID');
          setTracesStatus('Needs Project ID');
          setTraceDetailStatus('Needs Project ID and Trace ID');
        }
      })
      .catch((error) => {
        if (!isMounted) return;
        if (
          !(
            error.name === 'AbortError' ||
            error.message?.includes('fetch aborted') ||
            error.message?.includes('cancelled') ||
            error.message?.includes('navigation')
          )
        ) {
          setAuthStatus(`Error checking session: ${error.message}`);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [userFullName, loginMethodUsed]);

  const handleSignIn = async (type: LoginType) => {
    if (!apiUrl) {
      setAuthStatus('Error: API URL not set.');
      return;
    }

    localStorage.setItem('loginMethodUsed', type);
    setLoginMethodUsed(type);

    try {
      const response = await fetch(`${authBaseUrl}/oauth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: type, redirect_to: '/simple-login' }),
      });

      if (!response.ok) {
        let errorBody = `OAuth initiation failed: ${response.status}`;
        try {
          const body = await response.json();
          errorBody = body.detail || JSON.stringify(body);
        } catch (e) {
          /* ignore */
        }
        throw new Error(errorBody);
      }

      const responseData = await response.json();
      if (responseData.url) {
        setAuthStatus(`Redirecting to ${type}...`);
        window.location.href = responseData.url;
      } else {
        throw new Error('Backend did not return a valid redirect URL.');
      }
    } catch (error: any) {
      console.error(`${type} Sign-In Initiation Error:`, error);
      setAuthStatus(`Error starting ${type} sign in: ${error.message}`);
      toast({ title: 'Sign-In Error', description: error.message, variant: 'destructive' });
      localStorage.removeItem('loginMethodUsed');
      setLoginMethodUsed(null);
    }
  };

  const handleSignOut = async () => {
    setAuthStatus('Signing out...');
    try {
      await fetchAuthenticatedApi('/auth/logout', { method: 'POST' });
      setAuthStatus('Signed out successfully.');
      setIsSignedIn(false);
      setUserFullName(null);
      localStorage.removeItem('loginMethodUsed');
      setLoginMethodUsed(null);
      clearProjects();
      clearMetrics();
      clearTraces();
      clearPlaceholder();
      clearTraceDetail();
      setProjectsStatus('Idle');
      setMetricsStatus('Needs Project ID');
      setTracesStatus('Needs Project ID');
      setTraceDetailStatus('Needs Project ID and Trace ID');
    } catch (error: any) {
      setAuthStatus(`Error signing out: ${error.message}`);
    }
  };

  const fetchApiData = async (
    endpoint: string,
    setStatus: (status: string) => void,
    setData: (data: any) => void,
    setError: (error: string | null) => void,
  ) => {
    setData(null);
    setError(null);
    setStatus('Fetching...');

    if (!isSignedIn) {
      const errorMsg = 'Not signed in. Please sign in first.';
      setError(errorMsg);
      setStatus('Fetch failed: Not Authenticated');
      return;
    }

    setStatus('Calling API...');
    try {
      const data = await fetchAuthenticatedApi<any>(endpoint);
      setData(data);
      setError(null);

      if (endpoint === '/opsboard/projects') {
        if (Array.isArray(data) && data.length > 0 && data[0].id) {
          const firstProjectId = data[0].id;
          setProjectIdForV4(firstProjectId);
          setStatus(
            `Success! (Found ${data.length} projects, using ${firstProjectId} for V4 tests)`,
          );
          if (metricsStatus.startsWith('Needs')) setMetricsStatus('Ready');
          if (tracesStatus.startsWith('Needs')) setTracesStatus('Ready');
          if (traceDetailStatus.startsWith('Needs') && firstTraceIdForDisplay) {
            setTraceDetailStatus('Ready');
          }
        } else {
          setProjectIdForV4(null);
          setStatus(
            `Success! (Found ${Array.isArray(data) ? data.length : 0} projects, but couldn't get ID)`,
          );
          setMetricsStatus('Needs Project ID');
          setTracesStatus('Needs Project ID');
          setTraceDetailStatus('Needs Project ID and Trace ID');
          setFirstTraceIdForDisplay(null);
        }
      } else if (endpoint.includes('/v4/traces') && !endpoint.includes('/v4/traces/')) {
        let traceCount = 0;
        let firstTraceId: string | null = null;
        if (data?.traces && Array.isArray(data.traces) && data.traces.length > 0) {
          traceCount = data.traces.length;
          firstTraceId = data.traces[0]?.trace_id || null;
        }

        setFirstTraceIdForDisplay(firstTraceId);

        let statusMsg = `Success! (Found ${traceCount} traces`;
        if (firstTraceId) {
          statusMsg += `, using ${firstTraceId} for detail test)`;
          if (projectIdForV4 && traceDetailStatus.startsWith('Needs')) {
            setTraceDetailStatus('Ready');
          }
        } else {
          statusMsg += `)`;
          setTraceDetailStatus('Needs Project ID and Trace ID');
        }
        setStatus(statusMsg);
      } else {
        let countInfo = '';
        if (Array.isArray(data)) {
          countInfo = `(Found ${data.length} items)`;
        } else if (typeof data === 'object' && data !== null) {
          if (endpoint.includes('/v4/traces/') && data.trace_id) {
            countInfo = `(Trace ID: ${data.trace_id})`;
          } else if (data.trace_count !== undefined) {
            countInfo = `(Trace Count: ${data.trace_count})`;
          } else {
            countInfo = '(Data received)';
          }
        } else {
          countInfo = '(Data received)';
        }
        setStatus(`Success! ${countInfo}`);
      }
    } catch (error: any) {
      console.error(`Fetch execution error for ${endpoint}:`, error);
      setError(`Fetch failed: ${error.message}`);
      setData(null);
      if (endpoint === '/opsboard/projects') {
        setProjectIdForV4(null);
        setMetricsStatus('Needs Project ID');
        setTracesStatus('Needs Project ID');
        setTraceDetailStatus('Needs Project ID and Trace ID');
        setFirstTraceIdForDisplay(null);
      } else if (endpoint.includes('/v4/traces') && !endpoint.includes('/v4/traces/')) {
        setFirstTraceIdForDisplay(null);
        setTraceDetailStatus('Needs Project ID and Trace ID');
      }
      setStatus('Fetch failed: API error');
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        setIsSignedIn(false);
        setUserFullName(null);
        setAuthStatus('Session expired or invalid.');
        setProjectsStatus('Idle');
        setMetricsStatus('Needs Project ID');
        setTracesStatus('Needs Project ID');
        setTraceDetailStatus('Needs Project ID and Trace ID');
        setProjectIdForV4(null);
        setFirstTraceIdForDisplay(null);
      }
    }
  };

  const handleFetchProjects = () =>
    fetchApiData('/opsboard/projects', setProjectsStatus, setProjectsData, setProjectsError);

  const handleFetchMetrics = () => {
    if (!projectIdForV4) {
      setMetricsError('Cannot fetch Metrics: Project ID not available. Fetch Projects first.');
      setMetricsStatus('Failed: Missing Project ID');
      return;
    }
    const endpoint = `/v4/meterics/project?project_id=${projectIdForV4}`;
    fetchApiData(endpoint, setMetricsStatus, setMetricsData, setMetricsError);
  };

  const handleFetchTraces = () => {
    if (!projectIdForV4) {
      setTracesError('Cannot fetch Traces: Project ID not available. Fetch Projects first.');
      setTracesStatus('Failed: Missing Project ID');
      return;
    }
    const endpoint = `/v4/traces?project_id=${projectIdForV4}`;
    fetchApiData(endpoint, setTracesStatus, setTracesData, setTracesError);
  };

  const clearProjects = () => {
    setProjectsStatus('Ready');
    setProjectsData(null);
    setProjectsError(null);
    setProjectIdForV4(null);
    setMetricsStatus('Needs Project ID');
    setMetricsData(null);
    setMetricsError(null);
    setTracesStatus('Needs Project ID');
    setTracesData(null);
    setTracesError(null);
    setTraceDetailStatus('Needs Project ID and Trace ID');
    setTraceDetailData(null);
    setTraceDetailError(null);
    setFirstTraceIdForDisplay(null);
  };
  const clearMetrics = () => {
    setMetricsStatus(projectIdForV4 ? 'Ready' : 'Needs Project ID');
    setMetricsData(null);
    setMetricsError(null);
  };
  const clearTraces = () => {
    setTracesStatus(projectIdForV4 ? 'Ready' : 'Needs Project ID');
    setTracesData(null);
    setTracesError(null);
    setTraceDetailStatus('Needs Project ID and Trace ID');
    setTraceDetailData(null);
    setTraceDetailError(null);
    setFirstTraceIdForDisplay(null);
  };
  const clearPlaceholder = () => {
    setPlaceholderStatus('Idle');
    setPlaceholderData(null);
    setPlaceholderError(null);
  };

  const clearTraceDetail = () => {
    const projReady = !!projectIdForV4;
    const traceListReady = !!(
      projReady &&
      tracesData &&
      tracesData.traces &&
      tracesData.traces.length > 0
    );
    setTraceDetailStatus(traceListReady ? 'Ready' : 'Needs Project ID and Trace ID');
    setTraceDetailData(null);
    setTraceDetailError(null);
    setFirstTraceIdForDisplay(null);
  };

  const handleFetchFirstTraceDetail = async () => {
    setTraceDetailStatus('Starting...');
    setTraceDetailData(null);
    setTraceDetailError(null);
    setFirstTraceIdForDisplay(null);

    let currentProjectId: string | null = projectIdForV4;
    let currentTracesData: any = tracesData;

    try {
      if (!currentProjectId) {
        setTraceDetailStatus('Fetching projects...');
        const projects = await fetchAuthenticatedApi<any>('/opsboard/projects');
        if (Array.isArray(projects) && projects.length > 0 && projects[0].id) {
          currentProjectId = projects[0].id;
        } else {
          throw new Error('No projects found or first project has no ID.');
        }
      }

      if (!currentTracesData) {
        setTraceDetailStatus('Fetching traces...');
        const endpoint = `/v4/traces?project_id=${currentProjectId}`;
        currentTracesData = await fetchAuthenticatedApi<any>(endpoint);
        if (
          !currentTracesData ||
          !currentTracesData.traces ||
          !Array.isArray(currentTracesData.traces) ||
          currentTracesData.traces.length === 0
        ) {
          throw new Error('No traces found for the first project.');
        }
      }

      const firstTraceId = currentTracesData.traces[0]?.trace_id;
      if (!firstTraceId) {
        setFirstTraceIdForDisplay(null);
        throw new Error('Could not get trace_id from the first trace.');
      }

      setFirstTraceIdForDisplay(firstTraceId);

      setTraceDetailStatus(`Fetching detail for trace ${firstTraceId}...`);
      const detailEndpoint = `/v4/traces/${firstTraceId}?project_id=${currentProjectId}`;
      const detailData = await fetchAuthenticatedApi<any>(detailEndpoint);

      setTraceDetailData(detailData);
      setTraceDetailError(null);
      setTraceDetailStatus(`Success! Fetched details for trace ${firstTraceId}`);
    } catch (error: any) {
      console.error('Error fetching trace detail sequence:', error);
      setTraceDetailError(`Sequence failed: ${error.message}`);
      setTraceDetailData(null);
      setTraceDetailStatus('Failed');
      if (error.message.includes('401') || error.status === 401) {
        setIsSignedIn(false);
        setUserFullName(null);
        setAuthStatus('Session expired or invalid during sequence.');
      }
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Simple Login & API Test (DEV ONLY)</h1>

      <AuthSection
        authStatus={authStatus}
        isSignedIn={isSignedIn}
        onSignIn={handleSignIn}
        onSignOut={handleSignOut}
        selectedLoginType={selectedLoginType}
        onLoginTypeChange={setSelectedLoginType}
      />

      {isSignedIn && (
        <>
          <ApiTestSection
            title="API Call: /opsboard/projects"
            status={projectsStatus}
            data={projectsData}
            error={projectsError}
            onFetch={handleFetchProjects}
            onClear={clearProjects}
            fetchButtonText="Fetch Projects"
            isFetchDisabled={
              !isSignedIn || projectsStatus.startsWith('Fetch') || projectsStatus === 'Idle'
            }
          />

          <ApiTestSection
            title="API Call: /v4/meterics/project"
            status={metricsStatus}
            data={metricsData}
            error={metricsError}
            onFetch={handleFetchMetrics}
            onClear={clearMetrics}
            fetchButtonText="Fetch Metrics"
            isFetchDisabled={
              !isSignedIn ||
              !projectIdForV4 ||
              metricsStatus.startsWith('Fetch') ||
              metricsStatus === 'Needs Project ID'
            }
          />

          <ApiTestSection
            title="API Call: /v4/traces"
            status={tracesStatus}
            data={tracesData}
            error={tracesError}
            onFetch={handleFetchTraces}
            onClear={clearTraces}
            fetchButtonText="Fetch Traces"
            isFetchDisabled={
              !isSignedIn ||
              !projectIdForV4 ||
              tracesStatus.startsWith('Fetch') ||
              tracesStatus === 'Needs Project ID'
            }
          />

          <ApiTestSection
            title={
              <>
                API Call: /v4/traces/
                <span
                  style={{
                    backgroundColor: firstTraceIdForDisplay ? 'lightgreen' : '#ffdddd',
                    padding: '1px 3px',
                    borderRadius: '3px',
                  }}
                >
                  {firstTraceIdForDisplay || '{traceId}'}
                </span>
                ?project_id=
                <span
                  style={{
                    backgroundColor: projectIdForV4 ? 'lightgreen' : '#ffdddd',
                    padding: '1px 3px',
                    borderRadius: '3px',
                  }}
                >
                  {projectIdForV4 || '{projectId}'}
                </span>
              </>
            }
            status={traceDetailStatus}
            data={traceDetailData}
            error={traceDetailError}
            onFetch={handleFetchFirstTraceDetail}
            onClear={clearTraceDetail}
            fetchButtonText="Test Trace Detail Fetch"
            isFetchDisabled={
              !isSignedIn ||
              !projectIdForV4 ||
              traceDetailStatus.startsWith('Fetch') ||
              traceDetailStatus.startsWith('Needs')
            }
            fetchStatusPrefix="Starting"
          />

          <ResultsDisplay
            title="Your Endpoint Here!"
            data={placeholderData}
            error={placeholderError}
            status={placeholderStatus}
            onClear={clearPlaceholder}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              <Button disabled>Your Test Button</Button>
              <code style={{ fontSize: '0.8em', background: '#eee', padding: '2px 4px' }}>
                Add test logic in: dashboard/app/simple-login/page.tsx
              </code>
            </div>
          </ResultsDisplay>
        </>
      )}

      <p style={{ marginTop: '20px', fontSize: '0.9em', color: 'gray' }}>
        Check browser console and network tab for details.
      </p>
    </div>
  );
};

// Conditionally choose which component to export as default
// if you export the dev one you cannot build the app, so either
// leave this here, or just delete the folder!
const SimpleLoginPage =
  process.env.NODE_ENV === 'development' ? SimpleLoginPageDev : SimpleLoginPageProd;

export default SimpleLoginPage;
