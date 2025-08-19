import { IUser } from '@/types/IUser';
import { fetchAuthenticatedApi, ApiError } from '../api-client'; // Import the new client

/**
 * Fetches the data for the currently authenticated user using the backend API.
 */
export const fetchUserAPI = async (): Promise<IUser | null> => {
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
