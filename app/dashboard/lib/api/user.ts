import { IUser } from '@/types/IUser';
import { fetchAuthenticatedApi, ApiError } from '../api-client'; // Import the new client

/**
 * Fetches the data for the currently authenticated user using the backend API.
 */
export const fetchUserAPI = async (): Promise<IUser | null> => {
  // In local/dev without an authenticated session, avoid hitting the backend
  // to reduce console noise and unnecessary network requests.
  if (typeof document !== 'undefined') {
    const hasSessionCookie = document.cookie?.includes('session_id=');
    if (!hasSessionCookie) {
      return null;
    }
  }

  const endpoint = '/opsboard/users/me'; // Correct backend endpoint

  try {
    const user = await fetchAuthenticatedApi<IUser>(endpoint, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    });

    return user || null;
  } catch (error) {
    console.error('[fetchUserAPI] Error fetching user:', error);
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      return null;
    }
    throw error;
  }
};
