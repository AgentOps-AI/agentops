'use client';

import AccountForm from './account-form';
import { useUser } from '@/hooks/queries/useUser';
import { Skeleton } from '@/components/ui/skeleton';
export default function UserSettings() {
  const { data: user, isLoading, error } = useUser();

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (error) {
    return (
      <p className="text-red-500">
        Error loading user data: {error.message}. Please try refreshing.
      </p>
    );
  }

  if (!user) {
    return 'Could not load user data. You might not be properly authenticated.';
  }

  return <AccountForm />;
}
