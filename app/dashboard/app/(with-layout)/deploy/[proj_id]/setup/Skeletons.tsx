import React from 'react';

export function SkeletonHeader() {
  return (
    <div className="relative">
      <div className="flex items-center gap-3 mt-5 mb-1">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse"></div>
        <div className="flex items-center gap-1 ml-3">
          <div className="w-3 h-3 bg-gray-200 rounded-full animate-pulse"></div>
          <div className="h-4 w-16 bg-gray-200 rounded animate-pulse"></div>
        </div>
      </div>
      <div className="h-6 w-64 bg-gray-200 rounded animate-pulse mb-10"></div>
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="mb-8 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
      <div className="h-5 w-32 bg-gray-200 rounded animate-pulse mb-4"></div>
      <div className="space-y-4">
        <div className="h-4 w-24 bg-gray-200 rounded animate-pulse"></div>
        <div className="h-10 w-full bg-gray-200 rounded animate-pulse"></div>
        <div className="h-4 w-32 bg-gray-200 rounded animate-pulse"></div>
        <div className="h-10 w-full bg-gray-200 rounded animate-pulse"></div>
        <div className="h-4 w-28 bg-gray-200 rounded animate-pulse"></div>
        <div className="h-10 w-full bg-gray-200 rounded animate-pulse"></div>
      </div>
    </div>
  );
}

export function SkeletonSourceCode() {
  return (
    <div className="mb-8 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
      <div className="h-5 w-24 bg-gray-200 rounded animate-pulse mb-4"></div>
      <div className="h-10 w-48 bg-gray-200 rounded animate-pulse"></div>
    </div>
  );
}

export function SkeletonDeployService() {
  return (
    <div className="mb-8 border border-[rgba(222,224,244,1)] rounded-lg bg-white p-6 shadow-sm">
      <div className="h-5 w-40 bg-gray-200 rounded animate-pulse mb-2"></div>
      <div className="h-4 w-full bg-gray-200 rounded animate-pulse mb-2"></div>
      <div className="h-4 w-3/4 bg-gray-200 rounded animate-pulse"></div>
    </div>
  );
} 