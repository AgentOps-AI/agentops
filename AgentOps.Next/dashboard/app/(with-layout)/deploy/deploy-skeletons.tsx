import React from 'react';
import { Skeleton } from '@/components/ui/skeleton';

export function DeployPageSkeleton() {
  return (
    <div className="flex max-w-6xl flex-col gap-2 p-2">
      {/* Header section skeleton */}
      <Skeleton className="h-10 w-80 my-4" /> {/* Title */}
      <Skeleton className="h-5 w-96 mb-4" /> {/* Description */}
      
      {/* Buttons skeleton */}
      <div className="flex gap-4 my-4">
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-10 w-24" />
      </div>

      {/* Organizations section skeleton */}
      <div className="space-y-8">
        {Array.from({ length: 2 }).map((_, orgIndex) => (
          <OrgSectionSkeleton key={orgIndex} />
        ))}
      </div>
    </div>
  );
}

export function OrgSectionSkeleton() {
  return (
    <div>
      {/* Org header skeleton */}
      <div className="mb-4">
        <div className="flex items-center gap-3">
          <Skeleton className="h-6 w-40" /> {/* Org name */}
          <Skeleton className="h-6 w-16 rounded-full" /> {/* Subscription badge */}
        </div>
        <Skeleton className="h-4 w-24 mt-1" /> {/* Project count */}
      </div>

      {/* Projects grid skeleton */}
      <div className="mb-4 grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, projectIndex) => (
          <ProjectCardSkeleton key={projectIndex} />
        ))}
      </div>

      {/* More projects skeleton */}
      <div className="ml-6">
        <Skeleton className="h-4 w-28" /> {/* "more projects" text */}
      </div>
    </div>
  );
}

export function ProjectCardSkeleton() {
  return (
    <div className="relative flex flex-row items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 min-h-[72px] max-w-[420px]">
      {/* Left side - project info */}
      <div className="flex flex-col gap-0.5 w-full pr-4">
        <Skeleton className="h-5 w-32 mb-0.5" /> {/* Project name */}
        <Skeleton className="h-4 w-20" /> {/* Trace count */}
      </div>
      
      {/* Right side - status or action */}
      <div className="flex items-center gap-2">
        <Skeleton className="w-3 h-3 rounded-full" /> {/* Status dot */}
        <Skeleton className="h-4 w-16" /> {/* Status text or button */}
      </div>
    </div>
  );
}

export function LoadingSpinner() {
  return (
    <div className="mb-4">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600 dark:border-gray-600 dark:border-t-gray-400" />
    </div>
  );
}