'use client';

import { ProjectList } from './components/project-list';
import { useOrgs } from '@/hooks/queries/useOrgs';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorDisplay } from '@/components/ui/error-display';

export default function SettingsProjectsPage() {
  const { data: orgs, isLoading, error, refetch } = useOrgs();

  const pageHeader = (
    <div>
      <h3 className="text-lg font-medium" data-testid="projects-settings-header">
        Projects &amp; API Keys
      </h3>
      <p className="text-sm text-muted-foreground">
        Manage projects and their API keys for each organization.
      </p>
    </div>
  );

  if (isLoading) {
    return (
      <div className="space-y-3 md:max-w-3xl lg:space-y-6">
        {pageHeader}
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-3 md:max-w-3xl lg:space-y-6">
        {pageHeader}
        <ErrorDisplay
          error={error}
          message="We're unable to load your organizations at the moment. This might be due to a network issue or temporary server problem."
          onRetry={refetch}
          errorContext={{ component: 'SettingsProjectsPage', action: 'load_organizations' }}
          data-testid="projects-settings-error-message-orgs"
        />
      </div>
    );
  }

  if (!orgs || orgs.length === 0) {
    return (
      <div className="space-y-3 md:max-w-3xl lg:space-y-6">
        {pageHeader}
        <p data-testid="projects-settings-message-no-orgs">No organizations found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 md:max-w-3xl lg:space-y-6">
      {pageHeader}
      {orgs.map((org) => {
        return <ProjectList key={org.id} org={org} />;
      })}
    </div>
  );
}
