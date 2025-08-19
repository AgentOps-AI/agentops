'use client';

import { Tables } from '@/lib/types_db';
import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
  useMemo,
  useCallback,
} from 'react';
import { useProjects, projectsQueryKey } from '@/hooks/queries/useProjects';
import { useQueryClient } from '@tanstack/react-query';
import { IProject } from '@/types/IProject';
import { DateRange } from 'react-day-picker';

import { fetchAuthenticatedApi } from '@/lib/api-client';
import { IOrg } from '@/types/IOrg';

export interface GroupedProject {
  org_name: string;
  org_id: string;
  projects: (Tables<'projects'> & { session_count?: number })[];
}

export type ProjectWithCount = IProject & { session_count?: number };

export type ProjectContextType = {
  selectedProject: ProjectWithCount | null;
  setSelectedProject: (project: ProjectWithCount | null) => void;
  refreshProjects: () => Promise<void>;
  sharedDateRange: DateRange;
  setSharedDateRange: (range: DateRange) => void;
  activeOrgDetails: IOrg | null;
  isOrgDataLoading: boolean;
  orgFetchError: Error | null;
};

/**
 * Context for managing project-related data, including the currently selected project,
 * a shared date range for filtering data, and functions to update these values.
 */
const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

function getLocalStorageValue(item: string): ProjectWithCount | null {
  if (typeof window !== 'undefined') {
    const itemString = localStorage.getItem(item);
    if (!itemString) return null;
    try {
      const parsedItem = JSON.parse(itemString);
      if (
        item === 'selectedProject' &&
        parsedItem &&
        typeof parsedItem === 'object' &&
        'id' in parsedItem
      ) {
        return parsedItem as ProjectWithCount;
      }
      return null;
    } catch (e) {
      console.error('Error parsing localStorage item:', e);
      localStorage.removeItem(item);
      return null;
    }
  } else {
    return null;
  }
}

interface ProjectProviderProps {
  children: ReactNode;
}

/**
 * Provider component for project-related context.
 * Manages the selected project and shared date range, persisting them to localStorage.
 * It also handles fetching and refreshing the list of available projects.
 * Ensures that a valid project is selected by default and updates if the stored or current project becomes invalid.
 * Listens to localStorage changes to keep context in sync across tabs/windows.
 *
 * @param {ProjectProviderProps} props - The component props.
 * @param {ReactNode} props.children - The child components to render.
 * @returns {JSX.Element | null} The context provider wrapping children, or null if an error occurs.
 */
export default function ProjectProvider({ children }: ProjectProviderProps) {
  const { data: projects, isLoading: projectsLoading } = useProjects();
  const queryClient = useQueryClient();
  const [selectedProject, setSelectedProjectInternal] = useState<ProjectWithCount | null>(null);

  const initialSharedDateRange = useMemo(() => {
    // Create date 30 days ago at start of day
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    thirtyDaysAgo.setHours(0, 0, 0, 0);

    // Create date 24 hours in the future at end of day
    const tomorrowEnd = new Date(Date.now() + 24 * 60 * 60 * 1000);
    tomorrowEnd.setHours(23, 59, 59, 999);

    return { from: thirtyDaysAgo, to: tomorrowEnd };
  }, []);

  const [sharedDateRange, setSharedDateRangeInternal] = useState<DateRange>(initialSharedDateRange);

  const [activeOrgDetails, setActiveOrgDetails] = useState<IOrg | null>(null);
  const [isOrgDataLoading, setIsOrgDataLoading] = useState<boolean>(true);
  const [orgFetchError, setOrgFetchError] = useState<Error | null>(null);

  const setSelectedProject = useCallback(
    (project: ProjectWithCount | null) => {
      setSelectedProjectInternal(project);
      if (typeof window !== 'undefined') {
        if (project) {
          localStorage.setItem('selectedProject', JSON.stringify(project));
        } else {
          localStorage.removeItem('selectedProject');
        }
      }
    },
    [setSelectedProjectInternal],
  );

  const setSharedDateRange = useCallback(
    (range: DateRange) => {
      if (
        range &&
        range.from &&
        range.to &&
        !isNaN(new Date(range.from).getTime()) &&
        !isNaN(new Date(range.to).getTime())
      ) {
        setSharedDateRangeInternal(range);
      } else {
        console.warn('Attempted to set invalid sharedDateRange', range);
      }
    },
    [setSharedDateRangeInternal],
  );

  const refreshProjects = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: projectsQueryKey });
  }, [queryClient]);

  useEffect(() => {
    if (projectsLoading || !projects) {
      return;
    }

    let projectToSet: ProjectWithCount | null = null;
    let needsUpdate = false;

    if (selectedProject === null) {
      const storedProject = getLocalStorageValue('selectedProject') as ProjectWithCount | null;
      if (storedProject) {
        const isValidStoredProject = projects.some((p) => p.id === storedProject.id);
        if (isValidStoredProject) {
          projectToSet = storedProject;
        } else {
          localStorage.removeItem('selectedProject');
        }
      }
      if (!projectToSet && projects.length > 0) {
        projectToSet = projects[0];
      }
      needsUpdate = true;
    } else {
      const currentSelectedStillValid = projects.some((p) => p.id === selectedProject.id);
      if (!currentSelectedStillValid) {
        projectToSet = projects.length > 0 ? projects[0] : null;
        needsUpdate = true;
      }
    }

    if (needsUpdate && projectToSet?.id !== selectedProject?.id) {
      setSelectedProjectInternal(projectToSet);
    }
  }, [projects, projectsLoading]);

  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === 'selectedProject') {
        const newProject = getLocalStorageValue('selectedProject') as ProjectWithCount | null;
        if (JSON.stringify(newProject) !== JSON.stringify(selectedProject)) {
          setSelectedProjectInternal(newProject);
        }
      }
    };
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [selectedProject]);

  useEffect(() => {
    const fetchActiveOrg = async () => {
      setIsOrgDataLoading(true);
      setOrgFetchError(null);
      try {
        const orgId = selectedProject?.org_id || selectedProject?.org?.id;
        if (orgId) {
          const org = await fetchAuthenticatedApi<IOrg>(`/opsboard/orgs/${orgId}`);
          setActiveOrgDetails(org);
        } else {
          setActiveOrgDetails(null);
        }
      } catch (error: any) {
        console.error('Failed to fetch organization details:', error);
        setOrgFetchError(error);
      } finally {
        setIsOrgDataLoading(false);
      }
    };

    if (selectedProject) {
      fetchActiveOrg();
    } else {
      setIsOrgDataLoading(false);
    }
  }, [selectedProject]);

  const contextValue = useMemo(
    () => ({
      selectedProject: selectedProject,
      setSelectedProject: setSelectedProject,
      refreshProjects: refreshProjects,
      sharedDateRange: sharedDateRange,
      setSharedDateRange: setSharedDateRange,
      activeOrgDetails,
      isOrgDataLoading,
      orgFetchError,
    }),
    [
      selectedProject,
      setSelectedProject,
      refreshProjects,
      sharedDateRange,
      setSharedDateRange,
      activeOrgDetails,
      isOrgDataLoading,
      orgFetchError,
    ],
  );

  try {
    return <ProjectContext.Provider value={contextValue}>{children}</ProjectContext.Provider>;
  } catch (error) {
    console.error('ProjectProvider Error:', error);
    return null;
  }
}

/**
 * Custom hook to access the project context.
 * Provides an error if used outside of a ProjectProvider.
 * @returns {ProjectContextType} The project context, including selected project, date range, and update functions.
 */
export const useProject = () => {
  const context = useContext(ProjectContext);

  if (context === undefined) {
    throw new Error('useProject must be used inside ProjectProvider');
  }

  return context;
};
