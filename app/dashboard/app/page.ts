import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

// Define MFA Factor type here (or move to shared location like lib/interfaces.ts)
interface _MfaFactor {
  id: string;
  status: 'verified' | 'unverified';
  friendly_name?: string;
  factor_type: 'totp' | string;
}

// Define UserInfo based on expected /opsboard/users/me response
interface UserInfo {
  id: string;
  email?: string;
  survey_is_complete?: boolean | null;
  // Add other relevant fields like MFA status if returned by this endpoint
}

// This is a root page (server component) that runs before layout
export default async function RootPage() {
  // Await cookies() if linter expects a Promise
  const cookieStore = await cookies();
  const sessionId = cookieStore.get('session_id')?.value;

  // 1. If no session cookie, definitely redirect to signin
  if (!sessionId) {
    return redirect('/signin');
  }

  // 2. If cookie exists, verify session and get info from backend
  let userInfo: UserInfo | null = null;
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      throw new Error('API URL not configured');
    }

    // Fetch user info from /opsboard/users/me to verify session
    const response = await fetch(`${apiUrl}/opsboard/users/me`, {
      headers: {
        Cookie: `session_id=${sessionId}`,
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      // If status is 401/403, it means session is invalid/missing
      if (response.status === 401 || response.status === 403) {
        return redirect('/signin');
      } else {
        // Other error (500, 404 on the endpoint itself, etc.)
        throw new Error(`Failed to fetch user info: ${response.status} ${response.statusText}`);
      }
    }

    userInfo = await response.json();

    if (!userInfo) {
      // Should not happen if response.ok, but handle defensively
      throw new Error('Received empty user info from backend.');
    }
  } catch (error) {
    console.error('Error verifying session with /opsboard/users/me:', error);
    // Fallback: redirect to signin on any error during check
    return redirect('/signin?error=session_check_failed');
  }

  // 3. Redirect based on user info (assuming /opsboard/users/me implies authenticated)
  // NOTE: MFA check needs adjustment if /opsboard/users/me doesn't return factor/MFA status
  // For now, let's assume if we get user info, they are authenticated and skip MFA check
  // TODO: Re-implement MFA check based on data returned by /opsboard/users/me or add separate MFA status check

  // const factors = userInfo.factors || []; // Adjust based on actual UserInfo structure
  // const isMfaSetUp = ...
  // const isMfaVerifiedForSession = ...

  // if (isMfaSetUp && !isMfaVerifiedForSession) {
  //   return redirect('/mfa');
  // }

  // Check if user has completed the welcome survey
  if (userInfo.survey_is_complete === false || userInfo.survey_is_complete === null) {
    return redirect('/welcome');
  }

  // If authenticated and survey is complete, proceed to main app
  return redirect('/projects');
}
