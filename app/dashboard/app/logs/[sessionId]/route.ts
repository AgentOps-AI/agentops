import { NextResponse, NextRequest } from 'next/server';
import { captureException } from '@sentry/nextjs';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }, // Wrap params type in Promise
) {
  const { sessionId } = await params;
  if (!sessionId) {
    return new Response('Session ID is required', { status: 400 });
  }

  try {
    // Get the session_id cookie from the incoming request
    const sessionCookie = request.cookies.get('session_id');
    const token = sessionCookie?.value;

    if (!token) {
      // No session cookie found, user is not authenticated
      return new Response('Authentication required', { status: 401 });
    }

    // Construct the internal API URL
    // TODO: Use environment variable for API base URL
    const internalApiBaseUrl = process.env.INTERNAL_API_URL || request.nextUrl.origin; // Fallback to origin
    const logsApiUrl = `${internalApiBaseUrl}/api/logs/${sessionId}`; // Assuming backend route is /api/logs/:sessionId

    // Fetch logs from the internal API, forwarding the session_id cookie value as Bearer token
    const logsResponse = await fetch(logsApiUrl, {
      method: 'GET',
      headers: {
        // Send the session_id as the Bearer token
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        // Forward other necessary headers from the original request if needed
      },
      // IMPORTANT: Since this is a server-to-server request, we usually don't forward browser cookies
      // unless the internal API specifically relies on them (unlikely if using Bearer token).
    });

    if (!logsResponse.ok) {
      const errorText = await logsResponse.text();
      console.error(`Error fetching from internal logs API (${logsResponse.status}): ${errorText}`);
      captureException(new Error(`Logs API fetch failed: ${logsResponse.status}`), {
        extra: { errorText },
      });
      return new Response(`Failed to fetch logs: ${logsResponse.statusText}`, {
        status: logsResponse.status,
      });
    }

    const logsData = await logsResponse.json();
    return NextResponse.json(logsData);
  } catch (error: any) {
    console.error('Error in logs route handler:', error);
    captureException(error);
    return new Response('Internal Server Error', { status: 500 });
  }
}
