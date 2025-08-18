import { IOrg } from '@/types/IOrg';
import { fetchAuthenticatedApi, ApiError } from '@/lib/api-client';

/**
 * Fetches the list of organizations for the authenticated user.
 * Uses JWT authentication via fetchAuthenticatedApi.
 */
export const fetchOrgsAPI = async (): Promise<IOrg[]> => {
  try {
    const orgs = await fetchAuthenticatedApi<IOrg[]>('/opsboard/orgs');
    return orgs ?? [];
  } catch (error) {
    console.error('Error fetching organizations:', error);
    if (error instanceof ApiError) {
      throw new Error(
        `Failed to fetch organizations: ${error.status} - ${JSON.stringify(error.responseBody)}`,
      );
    } else {
      throw error;
    }
  }
};

export interface IOrgInviteResponse {
  inviter_id: string;
  invitee_email: string;
  org_id: string;
  role: string;
  org_name: string;
  created_at?: string;
}

export interface IOrgInviteWithEmails {
  invitee_email: string;
  inviter_email: string;
  role: string;
  org_id: string;
  org_name: string;
  created_at?: string;
  user_exists?: boolean;
}

export interface IUserOrg {
  user_id: string;
  org_id: string;
  role: string;
  user_email: string;
  is_paid: boolean;
}

export interface IOrgDetailResponse extends IOrg {
  users: IUserOrg[];
}

export const fetchOrgDetailAPI = async (orgId: string): Promise<IOrgDetailResponse | null> => {
  if (!orgId) {
    console.error('[fetchOrgDetailAPI] Org ID is required.');
    return null;
  }
  const endpoint = `/opsboard/orgs/${orgId}`;
  try {
    const orgDetail = await fetchAuthenticatedApi<IOrgDetailResponse>(endpoint, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return orgDetail || null;
  } catch (error) {
    console.error(`[fetchOrgDetailAPI] Error fetching details for org ${orgId}:`, error);
    if (
      error instanceof ApiError &&
      (error.status === 401 || error.status === 403 || error.status === 404)
    ) {
      return null;
    }
    throw error;
  }
};

export const fetchOrgInvitesAPI = async (): Promise<IOrgInviteResponse[] | null> => {
  const endpoint = '/opsboard/orgs/invites';
  try {
    const invites = await fetchAuthenticatedApi<IOrgInviteResponse[]>(endpoint, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return invites || [];
  } catch (error) {
    console.error('[fetchOrgInvitesAPI] Error fetching invites:', error);
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      return null;
    }
    throw error;
  }
};

export const fetchMyPendingInvitesAPI = fetchOrgInvitesAPI;

export interface CreateOrgPayload {
  name: string;
}

export const createOrgAPI = async (payload: CreateOrgPayload): Promise<IOrg | null> => {
  const endpoint = '/opsboard/orgs/create';
  try {
    const createdOrg = await fetchAuthenticatedApi<IOrg>(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return createdOrg || null;
  } catch (error) {
    console.error('[createOrgAPI] Error creating org:', error);
    throw error;
  }
};

export const acceptOrgInviteAPI = async (
  orgId: string,
): Promise<{ success: boolean; message?: string } | null> => {
  const endpoint = `/opsboard/orgs/${orgId}/accept`;
  try {
    const response = await fetchAuthenticatedApi<{ success: boolean; message?: string }>(endpoint, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
      },
    });
    return response || { success: false, message: 'No response from API' };
  } catch (error) {
    console.error(`[acceptOrgInviteAPI] Error accepting invite for org ${orgId}:`, error);
    if (error instanceof ApiError) {
      if (error.status === 401) {
        return {
          success: false,
          message: 'Authentication required. Your session may still be initializing.',
        };
      } else if (error.status === 404) {
        return {
          success: false,
          message: 'Invitation not found. It may have been revoked or already accepted.',
        };
      } else if (error.status === 400) {
        return {
          success: false,
          message: error.responseBody?.detail || 'Invalid invitation request.',
        };
      }
      return { success: false, message: error.message || `API Error ${error.status}` };
    }
    throw error;
  }
};

export interface UpdateOrgPayload {
  name: string;
}

export const updateOrgAPI = async (
  orgId: string,
  payload: UpdateOrgPayload,
): Promise<IOrg | null> => {
  if (!orgId) {
    console.error('[updateOrgAPI] Org ID is required.');
    return null;
  }
  const endpoint = `/opsboard/orgs/${orgId}/update`;
  try {
    const updatedOrg = await fetchAuthenticatedApi<IOrg>(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return updatedOrg || null;
  } catch (error) {
    console.error(`[updateOrgAPI] Error updating org ${orgId}:`, error);
    throw error;
  }
};

export interface InviteOrgMemberPayload {
  email: string;
  role: string;
}

export const inviteOrgMemberAPI = async (
  orgId: string,
  payload: InviteOrgMemberPayload,
): Promise<{ success: boolean; message?: string } | null> => {
  if (!orgId) {
    console.error('[inviteOrgMemberAPI] Org ID is required.');
    return { success: false, message: 'Org ID is required' };
  }
  const endpoint = `/opsboard/orgs/${orgId}/invite`;
  try {
    const normalizedPayload = {
      ...payload,
      email: payload.email.toLowerCase(),
    };
    const response = await fetchAuthenticatedApi<{ success: boolean; message?: string }>(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(normalizedPayload),
    });
    return response || { success: false, message: 'No response from API' };
  } catch (error) {
    console.error(`[inviteOrgMemberAPI] Error inviting user to org ${orgId}:`, error);
    if (error instanceof ApiError) {
      return {
        success: false,
        message: error.responseBody?.detail || error.message || `API Error ${error.status}`,
      };
    }
    throw error;
  }
};

export interface RemoveOrgMemberPayload {
  user_id: string;
}

export const removeOrgMemberAPI = async (
  orgId: string,
  payload: RemoveOrgMemberPayload,
): Promise<{ success: boolean; message?: string } | null> => {
  if (!orgId) {
    console.error('[removeOrgMemberAPI] Org ID is required.');
    return { success: false, message: 'Org ID is required' };
  }
  const endpoint = `/opsboard/orgs/${orgId}/members/remove`;
  try {
    const response = await fetchAuthenticatedApi<{ success: boolean; message?: string }>(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return response || { success: false, message: 'No response from API' };
  } catch (error) {
    console.error(`[removeOrgMemberAPI] Error removing user from org ${orgId}:`, error);
    if (error instanceof ApiError) {
      return {
        success: false,
        message: error.responseBody?.detail || error.message || `API Error ${error.status}`,
      };
    }
    throw error;
  }
};

export interface UpdateOrgMemberRolePayload {
  user_id: string;
  role: string;
}

export const updateOrgMemberRoleAPI = async (
  orgId: string,
  payload: UpdateOrgMemberRolePayload,
): Promise<{ success: boolean; message?: string } | null> => {
  if (!orgId) {
    console.error('[updateOrgMemberRoleAPI] Org ID is required.');
    return { success: false, message: 'Org ID is required' };
  }
  const endpoint = `/opsboard/orgs/${orgId}/members/update`;
  try {
    const response = await fetchAuthenticatedApi<{ success: boolean; message?: string }>(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return response || { success: false, message: 'No response from API' };
  } catch (error) {
    console.error(`[updateOrgMemberRoleAPI] Error updating role in org ${orgId}:`, error);
    if (error instanceof ApiError) {
      return {
        success: false,
        message: error.responseBody?.detail || error.message || `API Error ${error.status}`,
      };
    }
    throw error;
  }
};

// --- Add Delete Org API Function ---
export async function deleteOrgAPI(orgId: string): Promise<{ success: boolean; message?: string }> {
  // Assuming fetchAuthenticatedApi handles response parsing and error throwing
  return fetchAuthenticatedApi<{ success: boolean; message?: string }>(`/opsboard/orgs/${orgId}`, {
    method: 'DELETE',
  });
}
// --- End Delete Org API Function ---

export const fetchOrgInvitesForOrgAPI = async (orgId: string): Promise<IOrgInviteWithEmails[]> => {
  if (!orgId) {
    console.error('[fetchOrgInvitesForOrgAPI] Org ID is required.');
    return [];
  }
  const endpoint = `/opsboard/orgs/${orgId}/invites`;
  try {
    const invites = await fetchAuthenticatedApi<IOrgInviteWithEmails[]>(endpoint, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return invites || [];
  } catch (error) {
    console.error(`[fetchOrgInvitesForOrgAPI] Error fetching invites for org ${orgId}:`, error);
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      return [];
    }
    throw error;
  }
};

/**
 * Fetches pending invitations sent BY an organization (for admins to manage).
 * This is an alias for fetchOrgInvitesForOrgAPI with a clearer name.
 */
export const fetchOrgSentInvitesAPI = fetchOrgInvitesForOrgAPI;

export const revokeOrgInviteAPI = async (
  orgId: string,
  email: string,
): Promise<{ success: boolean; message?: string }> => {
  if (!orgId || !email) {
    console.error('[revokeOrgInviteAPI] Org ID and email are required.');
    return { success: false, message: 'Org ID and email are required' };
  }
  const normalizedEmail = email.toLowerCase();
  const endpoint = `/opsboard/orgs/${orgId}/invites/${encodeURIComponent(normalizedEmail)}`;
  try {
    const response = await fetchAuthenticatedApi<{ success: boolean; message?: string }>(endpoint, {
      method: 'DELETE',
      headers: { Accept: 'application/json' },
    });
    return response || { success: false, message: 'No response from API' };
  } catch (error) {
    console.error(
      `[revokeOrgInviteAPI] Error revoking invite for ${email} in org ${orgId}:`,
      error,
    );
    if (error instanceof ApiError) {
      return {
        success: false,
        message: error.responseBody?.detail || error.message || `API Error ${error.status}`,
      };
    }
    throw error;
  }
};

export interface PreviewMemberAddCostResponse {
  immediate_charge: number;
  next_period_charge: number;
  billing_interval: string;
  period_end?: string;
  currency: string;
}

export const previewMemberAddCostAPI = async (
  orgId: string,
): Promise<PreviewMemberAddCostResponse | null> => {
  if (!orgId) {
    console.error('[previewMemberAddCostAPI] Org ID is required.');
    return null;
  }
  const endpoint = `/opsboard/orgs/${orgId}/preview-member-cost`;
  try {
    const response = await fetchAuthenticatedApi<PreviewMemberAddCostResponse>(endpoint, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return response || null;
  } catch (error) {
    console.error(
      `[previewMemberAddCostAPI] Error fetching preview member add cost for org ${orgId}:`,
      error,
    );
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      return null;
    }
    throw error;
  }
};
