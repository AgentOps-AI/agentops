import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

// Define a minimal Project type (adapt if needed based on API response)
interface Project {
  id: string;
  name: string;
  // add other relevant fields
}

// Server-side helper to fetch authenticated API data
// NOTE: This duplicates some logic from api-client.ts but avoids making layout.tsx a client component
// Consider extracting shared logic if this pattern repeats often.
async function fetchServerSideApi<T = any>(endpoint: string): Promise<T> {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get('session_id')?.value;

  if (!sessionId) {
    // If called from a protected context, this implies an issue, maybe redirect?
    // Or let the API call fail with 401, which might be handled by the caller.
    throw new Error('User is not authenticated (no session cookie found server-side).');
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    throw new Error('NEXT_PUBLIC_API_URL environment variable is not set.');
  }

  const targetUrl = `${apiUrl}${endpoint}`;
  const response = await fetch(targetUrl, {
    headers: {
      // Send session_id as Bearer token
      Authorization: `Bearer ${sessionId}`,
      'Content-Type': 'application/json',
    },
    cache: 'no-store', // Prevent caching sensitive data by default
  });

  if (!response.ok) {
    let errorBody = `API request failed with status ${response.status}`;
    try {
      const body = await response.json();
      errorBody = body.detail || JSON.stringify(body);
    } catch (e) {
      /* ignore */
    }
    // Consider custom error class like ApiError used client-side
    throw new Error(errorBody);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json();
}

export default async function RequiresProjectLayout({ children }: { children: React.ReactNode }) {
  try {
    // Replace getProjects call with server-side API fetch
    const projects = await fetchServerSideApi<Project[]>('/opsboard/projects');

    if (!projects || projects.length === 0) {
      // If no projects, redirect to a page where they can create one
      redirect('/get-started'); // Or /create-project?
    }
  } catch (error) {
    console.error('Error fetching projects in layout:', error);
    // Handle error appropriately - maybe redirect to signin or an error page?
    // If fetchServerSideApi throws due to no cookie, middleware *should* have caught it,
    // but maybe redirect just in case.
    redirect('/signin?error=project_load_failed');
  }

  // If projects exist, render children
  return <>{children}</>;
}
