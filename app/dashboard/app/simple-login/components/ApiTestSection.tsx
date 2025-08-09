'use client';

import React, { ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import ResultsDisplay from './ResultsDisplay';

interface ApiTestSectionProps {
  title: ReactNode;
  status: string;
  data: any;
  error: string | null;
  onFetch: () => void;
  onClear: () => void;
  fetchButtonText: string;
  isFetchDisabled: boolean;
  fetchStatusPrefix?: string; // Optional: check status against this prefix for disabling during fetch
}

export const ApiTestSection: React.FC<ApiTestSectionProps> = ({
  title,
  status,
  data,
  error,
  onFetch,
  onClear,
  fetchButtonText,
  isFetchDisabled,
  fetchStatusPrefix = 'Fetching', // Default prefix to check
}) => {
  const isFetching = status.startsWith(fetchStatusPrefix);

  return (
    <ResultsDisplay title={title} status={status} data={data} error={error} onClear={onClear}>
      <Button onClick={onFetch} disabled={isFetchDisabled || isFetching}>
        {fetchButtonText}
      </Button>
    </ResultsDisplay>
  );
};

export default ApiTestSection;
