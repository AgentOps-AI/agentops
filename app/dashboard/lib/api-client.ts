import * as Sentry from '@sentry/nextjs';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export class ApiError extends Error {
  status: number;
  responseBody: any;
  endpoint: string;

  constructor(message: string, status: number, responseBody?: any, endpoint?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.responseBody = responseBody;
    this.endpoint = endpoint || 'unknown';
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ApiError);
    }
  }
}

/**
 * Creates a user-friendly error message based on the error type and status
 */
function getUserFriendlyErrorMessage(error: any, endpoint: string): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        return 'Your session has expired. Please sign in again.';
      case 403:
        return "You don't have permission to access this resource.";
      case 404:
        return 'The requested resource was not found.';
      case 429:
        return 'Too many requests. Please wait a moment and try again.';
      case 500:
        return 'A server error occurred. Our team has been notified.';
      case 502:
      case 503:
      case 504:
        return 'The service is temporarily unavailable. Please try again in a few moments.';
      default:
        return 'An unexpected error occurred. Please try again.';
    }
  }
  
  // Network or other errors
  if (error.message?.includes('fetch')) {
    return 'Unable to connect to the server. Please check your internet connection and try again.';
  }
  
  return 'An unexpected error occurred. Please try again.';
}

/**
 * Reports error to Sentry with additional context
 */
function reportErrorToSentry(error: any, endpoint: string, context: Record<string, any> = {}) {
  Sentry.withScope((scope: any) => {
    scope.setTag('error_source', 'api_client');
    scope.setTag('endpoint', endpoint);
    scope.setContext('api_request', {
      endpoint,
      url: `${API_URL}${endpoint}`,
      ...context,
    });
    
    if (error instanceof ApiError) {
      scope.setTag('api_status', error.status);
      scope.setLevel('error');
      scope.setContext('response_body', error.responseBody);
    } else {
      scope.setTag('error_type', 'network_error');
      scope.setLevel('error');
    }
    
    Sentry.captureException(error);
  });
}

/**
 * Performs an authenticated fetch request to the backend API using a session cookie.
 * Handles retrieving the session_id cookie and adding the Authorization header.
 *
 * @param endpoint - The API endpoint path (e.g., '/opsboard/projects').
 * @param options - Optional fetch options (method, body, etc.). Defaults to GET.
 * @returns The JSON response data.
 * @throws {ApiError} If the API returns an error status or fetch fails.
 * @throws {Error} If session_id cookie is not found or API URL is missing.
 */
export async function fetchAuthenticatedApi<T = any>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  if (!API_URL) {
    throw new Error('NEXT_PUBLIC_API_URL environment variable is not set.');
  }

  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  const fetchOptions: RequestInit = {
    ...options,
    headers,
    credentials: 'include',
  };

  const targetUrl = `${API_URL}${endpoint}`;

  try {
    const response = await fetch(targetUrl, fetchOptions);
    if (!response.ok) {
      let errorBody;
      try {
        errorBody = await response.json();
      } catch (e) {
        try {
          errorBody = await response.text();
        } catch (readErr) {
          errorBody = 'Failed to read error response body';
        }
      }
      console.error(`[API Client] API Error ${response.status} for ${endpoint}:`, errorBody);
      throw new ApiError(
        `API request failed with status ${response.status}`,
        response.status,
        errorBody,
        endpoint,
      );
    }

    if (response.status === 204) {
      return undefined as T;
    }

    const data: T = await response.json();
    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      // Report API errors to Sentry with context
      reportErrorToSentry(error, endpoint, {
        status: error.status,
        responseBody: error.responseBody,
      });
      
      // Check for 401 Unauthorized specifically
      if (error.status === 401) {
        // Ensure this runs only on the client side
        if (typeof window !== 'undefined') {
          console.warn('[API Client] Received 401 Unauthorized for ${endpoint}.');
          // Prevent infinite loops if signin page itself triggers a 401 somehow
          if (window.location.pathname !== '/signin') {
            window.location.href = '/signin';
          }
          // Throw a specific error to signal the call failed due to auth and redirection occurred.
          throw new Error('Unauthorized. Redirecting to signin.');
        } else {
          // If not client-side (SSR/build), just re-throw the original error.
          // The caller might handle server-side redirection if needed.
          throw error;
        }
      }
      // Re-throw other ApiErrors with user-friendly message
      const userMessage = getUserFriendlyErrorMessage(error, endpoint);
      throw new Error(userMessage);
    } else {
      // Report network/unexpected errors to Sentry
      reportErrorToSentry(error, endpoint, {
        error_type: 'network_or_unexpected',
        original_message: (error as Error).message,
      });
      
      console.error(`[API Client] Network or unexpected error for ${endpoint}:`, error);
      const userMessage = getUserFriendlyErrorMessage(error, endpoint);
      throw new Error(userMessage);
    }
  }
}
