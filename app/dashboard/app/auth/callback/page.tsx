'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { acceptOrgInviteAPI } from '@/lib/api/orgs';

const getHashParams = (): Record<string, string> => {
  const hashParams: Record<string, string> = {};
  if (typeof window !== 'undefined') {
    const hash = window.location.hash.substring(1); // Remove #
    const params = new URLSearchParams(hash);
    params.forEach((value, key) => {
      hashParams[key] = value;
    });
  }
  return hashParams;
};

export default function AuthCallbackPage() {
  const router = useRouter();
  const [message, setMessage] = useState('Processing sign-in...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const processAuth = async () => {
      const params = getHashParams();
      const accessToken = params['access_token'];
      const refreshToken = params['refresh_token'];
      const errorDescription = params['error_description'];

      // Also check for invite parameter in query string
      const urlParams = new URLSearchParams(window.location.search);
      const inviteFromQuery = urlParams.get('invite');

      console.log('Auth callback processing:', {
        hasAccessToken: !!accessToken,
        hasRefreshToken: !!refreshToken,
        inviteFromQuery,
        allParams: params,
      });

      if (errorDescription) {
        setError(`Sign-in error: ${errorDescription}`);
        setMessage('Redirecting to sign-in...');
        setTimeout(
          () => router.push('/signin?message=' + encodeURIComponent(`Error: ${errorDescription}`)),
          3000,
        );
        return;
      }

      if (!accessToken || !refreshToken) {
        setError('Authentication tokens not found in URL hash.');
        setMessage('Redirecting to sign-in...');
        console.error('Missing tokens in hash:', window.location.hash);
        setTimeout(
          () =>
            router.push(
              '/signin?message=' +
                encodeURIComponent('Error: Could not retrieve authentication tokens.'),
            ),
          3000,
        );
        return;
      }

      try {
        // Construct the full API URL for the /auth/session endpoint
        // Assuming NEXT_PUBLIC_API_URL is available and correctly set
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
        if (!apiUrl) {
          throw new Error('NEXT_PUBLIC_API_URL environment variable is not set.');
        }
        const sessionEndpoint = `${apiUrl}/auth/session`;

        // Make the POST request to the backend /auth/session endpoint
        // NOTE: We are NOT using fetchAuthenticatedApi here because we don't have the session_id cookie yet.
        // We need credentials: 'include' so the browser *receives* the Set-Cookie header from the backend.

        const urlParams = new URLSearchParams();
        for (const [key, value] of Object.entries(params)) {
          urlParams.append(key, value);
        }

        const response = await fetch(sessionEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: urlParams.toString(),
          credentials: 'include', // Important to receive the session cookie
        });

        if (!response.ok) {
          let errorBody = 'Failed to create session.';
          try {
            const body = await response.json();
            errorBody = body.detail || JSON.stringify(body); // Adapt based on actual backend error structure
          } catch (e) {
            // Ignore if response is not JSON
          }
          throw new Error(`Failed to create session: ${response.status} ${errorBody}`);
        }

        // If successful, the backend should have set the session_id cookie.
        // Redirect to the main application page.
        setMessage('Sign-in successful! Redirecting...');
        // Clear the hash to prevent accidental re-processing
        window.location.hash = '';

        let invitedToOrg = null;
        try {
          if (params['data']) {
            const decodedData = decodeURIComponent(params['data']);
            const parsedData = JSON.parse(decodedData);
            invitedToOrg = parsedData.invited_to_org;
          }

          if (!invitedToOrg && params['invited_to_org']) {
            invitedToOrg = params['invited_to_org'];
          }

          if (!invitedToOrg && accessToken) {
            try {
              const payload = JSON.parse(atob(accessToken.split('.')[1]));
              if (payload.user_metadata?.invited_to_org) {
                invitedToOrg = payload.user_metadata.invited_to_org;
              }
            } catch (e) {
              console.error('Failed to decode JWT:', e);
            }
          }
        } catch (e) {
          console.error('Failed to parse invite data:', e);
        }

        if (!invitedToOrg && inviteFromQuery) {
          invitedToOrg = inviteFromQuery;
        }

        if (invitedToOrg) {
          try {
            console.log(`Accepting invitation for organization: ${invitedToOrg}`);
            setMessage('Invitation detected, joining organization...');
            const acceptResponse = await acceptOrgInviteAPI(invitedToOrg);
            if (acceptResponse?.success) {
              console.log('Successfully accepted organization invite.');
              setMessage('Successfully joined organization! Redirecting...');
            } else {
              console.error('Failed to accept organization invite:', acceptResponse?.message);
              setError(`Could not automatically join organization: ${acceptResponse?.message}`);
            }
          } catch (e) {
            console.error('Error calling acceptOrgInviteAPI:', e);
            setError(`An error occurred while joining the organization.`);
          }
          const redirectUrl = `/`;
          router.push(redirectUrl);
        } else {
          router.push('/');
        }
      } catch (err: any) {
        console.error('Error calling /auth/session:', err);
        setError(`Error during sign-in: ${err.message}`);
        setMessage('Redirecting to sign-in...');
        setTimeout(
          () =>
            router.push('/signin?message=' + encodeURIComponent(`Sign-in failed: ${err.message}`)),
          3000,
        );
      }
    };

    processAuth();
  }, [router]);

  return (
    <div style={{ padding: '20px' }}>
      <h1>Sign In</h1>
      <p>{message}</p>
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
    </div>
  );
}
