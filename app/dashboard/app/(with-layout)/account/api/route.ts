import { NextRequest, NextResponse } from 'next/server';

interface UserDetails {
  id: string;
  email?: string;
}

export async function GET(request: NextRequest) {
  // Read cookie directly from the request object
  const sessionId = request.cookies.get('session_id')?.value;

  if (!sessionId) {
    return new NextResponse(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      throw new Error('API URL not configured');
    }

    // Fetch user details from backend, forwarding the session ID
    const response = await fetch(`${apiUrl}/auth/user-details`, {
      // Endpoint needs to exist on backend
      headers: {
        Authorization: `Bearer ${sessionId}`,
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      // Proxy the error status and message from the backend if possible
      const errorBody = await response.text();
      return new NextResponse(errorBody || `Error fetching user details: ${response.statusText}`, {
        status: response.status,
        headers: { 'Content-Type': response.headers.get('content-type') || 'application/json' },
      });
    }

    const userDetails: UserDetails = await response.json();
    return NextResponse.json(userDetails);
  } catch (error: any) {
    console.error('[API Route /account/api] Error:', error);
    return new NextResponse(JSON.stringify({ error: 'Internal Server Error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
