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
    // In development, 401 errors are expected when not logged in
    // Only log other errors or 401s in production
    const isDevelopment = process.env.NODE_ENV === 'development';
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      if (!isDevelopment) {
        console.error('[fetchUserAPI] Authentication error:', error.status);
      }
      return null;
    }
    console.error('[fetchUserAPI] Error fetching user:', error);
    throw error;
  }
};
