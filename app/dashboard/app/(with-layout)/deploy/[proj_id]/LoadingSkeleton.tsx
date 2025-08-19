import React from 'react';

// Loading Skeleton Components
const LoadingSkeleton = () => {
  return (
    <div className="relative font-['Figtree'] text-gray-900 dark:text-white mx-8 animate-pulse">
      {/* Header Actions Skeleton */}
      <div className="absolute top-5 right-5 flex items-center gap-2 z-10">
        <div className="w-9 h-9 bg-gray-200 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-700"></div>
        <div className="w-9 h-9 bg-gray-200 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-700"></div>
      </div>

      {/* Title and Status Skeleton */}
      <div className="flex items-center gap-3 mt-5 mb-1">
        <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded"></div>
        <div className="flex items-center gap-1 ml-3">
          <div className="w-3 h-3 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
          <div className="h-5 w-16 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
      
      {/* Organization Name Skeleton */}
      <div className="h-6 w-64 bg-gray-200 dark:bg-gray-700 rounded mb-10"></div>

      {/* Main Content Skeleton */}
      <div className="flex gap-6">
        {/* Left Column - Hosting Metrics */}
        <div className="flex-1 w-2/3">
          <div className="mt-0">
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <div className="h-6 w-32 bg-gray-200 dark:bg-gray-700 rounded mb-4"></div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                    <div className="h-4 w-20 bg-gray-200 dark:bg-gray-600 rounded mb-2"></div>
                    <div className="h-8 w-16 bg-gray-200 dark:bg-gray-600 rounded"></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Agent HTTP Client */}
        <div className="flex-none w-1/3">
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            <div className="h-6 w-32 bg-gray-200 dark:bg-gray-700 rounded mb-4"></div>
            <div className="space-y-4">
              <div className="h-4 w-24 bg-gray-200 dark:bg-gray-600 rounded"></div>
              <div className="h-32 bg-gray-50 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600"></div>
              <div className="h-10 bg-gray-200 dark:bg-gray-600 rounded"></div>
            </div>
          </div>
        </div>
      </div>

      {/* Deployment History Skeleton */}
      <div className="mt-8">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <div className="h-6 w-40 bg-gray-200 dark:bg-gray-700 rounded mb-4"></div>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 bg-gray-200 dark:bg-gray-600 rounded-full"></div>
                  <div className="h-4 w-32 bg-gray-200 dark:bg-gray-600 rounded"></div>
                </div>
                <div className="h-4 w-20 bg-gray-200 dark:bg-gray-600 rounded"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoadingSkeleton; 