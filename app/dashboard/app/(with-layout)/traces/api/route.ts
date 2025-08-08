import { NextRequest, NextResponse } from 'next/server';

// Helper function (copy or share)
async function fetchBackendApi(request: NextRequest, endpoint: string, options: RequestInit = {}) {
  const sessionId = request.cookies.get('session_id')?.value;
  if (!sessionId) {
    return new NextResponse(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });
  }
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return new NextResponse(
      JSON.stringify({ error: 'Internal Server Error: Configuration missing' }),
      { status: 500 },
    );
  }
  const targetUrl = new URL(`${apiUrl}${endpoint}`);
  if (options.method === 'GET' || !options.method) targetUrl.search = request.nextUrl.search;
  const headers = new Headers(options.headers || {});
  headers.set('Authorization', `Bearer ${sessionId}`);
  if (!headers.has('Content-Type') && options.body) headers.set('Content-Type', 'application/json');
  try {
    const response = await fetch(targetUrl.toString(), { ...options, headers, cache: 'no-store' });
    const responseBody = await response.text();
    const responseHeaders = new Headers();
    responseHeaders.set('Content-Type', response.headers.get('content-type') || 'application/json');
    return new NextResponse(responseBody, { status: response.status, headers: responseHeaders });
  } catch (error: any) {
    return new NextResponse(JSON.stringify({ error: 'Internal Server Error' }), { status: 500 });
  }
}

// GET traces/sessions
export async function GET(request: NextRequest) {
  // Forward the request directly to the backend /traces endpoint
  return fetchBackendApi(request, '/traces');
}

// POST to refresh sessions
export async function POST(request: NextRequest) {
  // Extract projectId if needed by the backend endpoint
  const { searchParams } = request.nextUrl;
  const projectId = searchParams.get('project_id');

  if (!projectId) {
    return new NextResponse(JSON.stringify({ error: 'Project ID is required for refresh' }), {
      status: 400,
    });
  }

  // Call the backend refresh endpoint
  return fetchBackendApi(request, `/traces/refresh?project_id=${projectId}`, {
    // Assuming this endpoint
    method: 'POST',
    // Body might not be needed if projectId is in query param
  });
}
