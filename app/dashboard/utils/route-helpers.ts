/**
 * Determines if a given route requires a selected project
 */
export const routeRequiresProject = (pathname: string | null): boolean => {
  if (!pathname) return false;
  return pathname.startsWith('/traces') || pathname.startsWith('/overview');
};

/**
 * Determines if the premium status banner should be shown for a given route
 */
export const shouldShowPremiumBanner = (pathname: string | null): boolean => {
  return routeRequiresProject(pathname);
};
