import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const imageUrl = searchParams.get('url');

  if (!imageUrl) {
    return new NextResponse('Missing image URL', { status: 400 });
  }

  try {
    const directResponse = await fetch(imageUrl);

    if (directResponse.ok) {
      const contentType = directResponse.headers.get('content-type') || 'application/octet-stream';
      const body: ReadableStream<Uint8Array> | null = directResponse.body;
      return new NextResponse(body, {
        status: directResponse.status,
        headers: {
          'Content-Type': contentType,
          'Cache-Control': 'public, max-age=3600',
        },
      });
    }

    if (directResponse.status === 401 || directResponse.status === 403) {
      console.error(
        `Direct fetch failed (${directResponse.status}), attempting authenticated proxy for: ${imageUrl}`,
      );
    } else {
      throw new Error(`Direct fetch failed: ${directResponse.status} ${directResponse.statusText}`);
    }
  } catch (error: any) {
    if (error.message?.includes('401') || error.message?.includes('403')) {
      console.error('Direct fetch failed, likely needs auth, proceeding to proxy attempt.');
    } else {
      console.error('Error during direct image fetch:', error);
      return new NextResponse('Failed to fetch image directly', { status: 500 });
    }
  }

  try {
    const sessionCookie = request.cookies.get('session_id');
    const sessionId = sessionCookie?.value;

    if (!sessionId) {
      console.warn('Image proxy attempt without session cookie.');
      return new NextResponse('Unauthorized (Missing Session)', { status: 401 });
    }

    const backendApiBaseUrl = process.env.BACKEND_API_URL || request.nextUrl.origin;
    const backendProxyUrl = new URL(`${backendApiBaseUrl}/api/storage-proxy`);
    backendProxyUrl.searchParams.set('url', imageUrl);

    const response = await fetch(backendProxyUrl.toString(), {
      headers: {
        Authorization: `Bearer ${sessionId}`,
      },
    });

    if (!response.ok) {
      console.error(
        `Backend image proxy failed (${response.status}): ${backendProxyUrl.toString()}`,
      );
      return new NextResponse(`Failed to proxy image: ${response.statusText}`, {
        status: response.status,
      });
    }

    const contentType = response.headers.get('content-type') || 'application/octet-stream';
    const body: ReadableStream<Uint8Array> | null = response.body;

    return new NextResponse(body, {
      status: response.status,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=3600',
      },
    });
  } catch (error) {
    console.error('Error in image proxy route (authenticated attempt):', error);
    return new NextResponse('Internal Server Error during proxy', { status: 500 });
  }
}
