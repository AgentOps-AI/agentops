import { NextRequest, NextResponse } from 'next/server';

// Helper function to call backend API from server-side route
// Avoids duplicating fetch logic in every route handler
// Uses request object to get session cookie
async function fetchBackendApi(request: NextRequest, endpoint: string, options: RequestInit = {}) {
  const sessionId = request.cookies.get('session_id')?.value;
  if (!sessionId) {
    return new NextResponse(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    console.error('[API Route Helper] API URL not configured');
    return new NextResponse(
      JSON.stringify({ error: 'Internal Server Error: Configuration missing' }),
      { status: 500 },
    );
  }

  const targetUrl = new URL(`${apiUrl}${endpoint}`);
  if (options.method === 'GET' || !options.method) {
    // Forward query params for GET requests
    targetUrl.search = request.nextUrl.search;
  }

  const headers = new Headers(options.headers || {});
  headers.set('Authorization', `Bearer ${sessionId}`);
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(targetUrl.toString(), {
      ...options,
      headers,
      cache: 'no-store',
    });

    // Proxy the response back to the client
    const responseBody = await response.text(); // Read body once
    const responseHeaders = new Headers();
    responseHeaders.set('Content-Type', response.headers.get('content-type') || 'application/json');

    return new NextResponse(responseBody, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error: any) {
    console.error(`[API Route Helper] Fetch error for ${endpoint}:`, error);
    return new NextResponse(JSON.stringify({ error: 'Internal Server Error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// GET handler for listing projects or getting default
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const getDefault = searchParams.get('default');

  if (getDefault === 'true') {
    // Fetch default project from backend
    return fetchBackendApi(request, '/opsboard/projects/default'); // Assuming this endpoint exists
  } else {
    // Fetch all projects from backend
    return fetchBackendApi(request, '/opsboard/projects');
  }
}

// POST handler for creating a new project
export async function POST(request: NextRequest) {
  let newProjectData;
  try {
    newProjectData = await request.json();
    if (!newProjectData || typeof newProjectData.name !== 'string' || !newProjectData.name.trim()) {
      return new NextResponse(JSON.stringify({ error: 'Project name is required' }), {
        status: 400,
      });
    }
  } catch (e) {
    return new NextResponse(JSON.stringify({ error: 'Invalid request body' }), { status: 400 });
  }

  // Call backend to create the project
  return fetchBackendApi(request, '/opsboard/projects', {
    method: 'POST',
    body: JSON.stringify({ name: newProjectData.name }), // Only forward necessary fields
  });
}
