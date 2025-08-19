import { IProject, IHostingProject } from '@/types/IProject';
import { fetchAuthenticatedApi, ApiError } from '@/lib/api-client';

/**
 * Fetches the list of projects for the authenticated user.
 * Uses JWT authentication via fetchAuthenticatedApi.
 */
export const fetchProjects = async (): Promise<IProject[]> => {
  try {
    const projects = await fetchAuthenticatedApi<IProject[]>('/opsboard/projects');
    return projects ?? [];
  } catch (error) {
    console.error('Error fetching projects:', error);
    if (error instanceof ApiError) {
      throw new Error(
        `Failed to fetch projects: ${error.status} - ${JSON.stringify(error.responseBody)}`,
      );
    } else {
      throw error;
    }
  }
};

export interface CreateProjectPayload {
  org_id: string;
  name: string;
}
export const createProjectAPI = async (payload: CreateProjectPayload): Promise<IProject> => {
  try {
    const createdProject = await fetchAuthenticatedApi<IProject>('/opsboard/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (!createdProject) {
      throw new Error('API did not return created project data.');
    }
    return createdProject;
  } catch (error) {
    console.error('Error creating project:', error);
    if (error instanceof ApiError) {
      throw new Error(
        'Failed to create project. Please try again or contact support if the issue persists.',
      );
    } else {
      throw error;
    }
  }
};

export interface DeleteProjectPayload {
  projectId: string;
}
export const deleteProjectAPI = async (
  payload: DeleteProjectPayload,
): Promise<{ success: boolean; message?: string }> => {
  try {
    // Use fetchAuthenticatedApi. Assuming 200/204 on success based on schema StatusResponse
    // The schema shows POST, adhering to that.
    const response = await fetchAuthenticatedApi<{ message?: string }>(
      `/opsboard/projects/${payload.projectId}/delete`,
      { method: 'POST' },
    );
    return { success: true, message: response?.message || 'Project deleted successfully' };
  } catch (error) {
    console.error('Error deleting project:', error);
    if (error instanceof ApiError) {
      return {
        success: false,
        message: `Failed to delete project: ${error.status} - ${JSON.stringify(error.responseBody)}`,
      };
    } else {
      return { success: false, message: (error as Error).message };
    }
  }
};

export interface RenameProjectPayload {
  projectId: string;
  newName: string;
}
export const renameProjectAPI = async (payload: RenameProjectPayload): Promise<IProject> => {
  try {
    const updatedProject = await fetchAuthenticatedApi<IProject>(
      `/opsboard/projects/${payload.projectId}/update`,
      {
        method: 'POST',
        body: JSON.stringify({ name: payload.newName }),
      },
    );
    if (!updatedProject) {
      throw new Error('API did not return updated project data.');
    }
    return updatedProject;
  } catch (error) {
    console.error('Error renaming project:', error);
    if (error instanceof ApiError) {
      throw new Error(
        `Failed to rename project: ${error.status} - ${JSON.stringify(error.responseBody)}`,
      );
    } else {
      throw error;
    }
  }
};

export interface RotateApiKeyPayload {
  projectId: string;
}
// Response should be the updated Project object according to schema
export const rotateApiKeyAPI = async (payload: RotateApiKeyPayload): Promise<IProject> => {
  try {
    const updatedProject = await fetchAuthenticatedApi<IProject>(
      `/opsboard/projects/${payload.projectId}/regenerate-key`,
      { method: 'POST' },
    );
    if (!updatedProject) {
      throw new Error('API did not return project data after key rotation.');
    }
    return updatedProject;
  } catch (error) {
    console.error('Error rotating API key:', error);
    if (error instanceof ApiError) {
      throw new Error(
        `Failed to rotate API key: ${error.status} - ${JSON.stringify(error.responseBody)}`,
      );
    } else {
      throw error;
    }
  }
};

export const fetchDeployments = async (): Promise<IHostingProject[]> => {
  try {
    const deployments = await fetchAuthenticatedApi<IHostingProject[]>('/deploy/deployments');
    return deployments ?? [];
  } catch (error) {
    console.error('Error fetching deployments:', error);
    if (error instanceof ApiError) {
      throw new Error(
        `Failed to fetch deployments: ${error.status} - ${JSON.stringify(error.responseBody)}`,
      );
    } else {
      throw error;
    }
  }
};

export interface DeploymentJob {
  id: string;
  queued_at: string;
  status: string;
  message: string;
}

export interface DeploymentHistoryResponse {
  jobs: DeploymentJob[];
}

export const fetchDeploymentHistory = async (projectId: string): Promise<DeploymentHistoryResponse> => {
  try {
    const history = await fetchAuthenticatedApi<DeploymentHistoryResponse>(`/deploy/deployments/${projectId}/history`);
    return history ?? { jobs: [] };
  } catch (error) {
    console.error('Error fetching deployment history:', error);
    if (error instanceof ApiError) {
      throw new Error(
        `Failed to fetch deployment history: ${error.status} - ${JSON.stringify(error.responseBody)}`,
      );
    } else {
      throw error;
    }
  }
};
