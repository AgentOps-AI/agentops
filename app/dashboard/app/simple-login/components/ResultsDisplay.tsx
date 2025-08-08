'use client';

import React, { useState, useEffect, ReactNode } from 'react';
import { Button } from '@/components/ui/button';

interface ResultsDisplayProps {
  title: ReactNode;
  data: any;
  error: string | null;
  status: string;
  children: ReactNode;
  onClear: () => void;
}

export const ResultsDisplay: React.FC<ResultsDisplayProps> = ({
  title,
  data,
  error,
  status,
  children,
  onClear,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(true);

  const hasContent = data || error;

  useEffect(() => {
    if (!hasContent) {
      setIsCollapsed(true);
    }
  }, [hasContent]);

  return (
    <div style={{ marginBottom: '10px', border: '1px dashed #ccc', padding: '10px' }}>
      <h2 style={{ marginTop: 0 }}>{title}</h2>
      <p>
        Status: <span style={{ fontWeight: 'bold' }}>{status}</span>
      </p>
      <div style={{ marginBottom: '10px', display: 'flex', gap: '10px', alignItems: 'center' }}>
        {children}
        {hasContent && (
          <Button onClick={onClear} variant="outline" size="sm">
            Clear
          </Button>
        )}
        {hasContent && (
          <Button onClick={() => setIsCollapsed(!isCollapsed)} variant="ghost" size="sm">
            {isCollapsed ? 'Show Details' : 'Hide Details'}
          </Button>
        )}
      </div>
      {!isCollapsed && error && (
        <div style={{ color: 'red', border: '1px solid red', padding: '10px', marginTop: '10px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}
      {!isCollapsed && data && (
        <div style={{ border: '1px solid green', padding: '10px', marginTop: '10px' }}>
          <strong>Data:</strong>
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
              background: '#f0f0f0',
              padding: '5px',
            }}
          >
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default ResultsDisplay;
