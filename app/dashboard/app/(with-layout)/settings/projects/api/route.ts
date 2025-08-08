import { NextRequest, NextResponse } from 'next/server';

// Helper function (copy from projects/api/route.ts or extract to shared lib)
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
    console.error(`[API Route Helper] Fetch error for ${endpoint}:`, error);
    return new NextResponse(JSON.stringify({ error: 'Internal Server Error' }), { status: 500 });
  }
}

// POST handler for rotating an API key
export async function POST(request: NextRequest) {
  let body;
  try {
    body = await request.json();
    if (!body || typeof body.projectId !== 'string') {
      return new NextResponse(JSON.stringify({ error: 'Project ID is required' }), { status: 400 });
    }
  } catch (e) {
    return new NextResponse(JSON.stringify({ error: 'Invalid request body' }), { status: 400 });
  }

  // Call backend to rotate the key
  return fetchBackendApi(request, `/projects/${body.projectId}/rotate-key`, {
    method: 'POST',
    // No body needed if projectId is in the URL
  });
}
