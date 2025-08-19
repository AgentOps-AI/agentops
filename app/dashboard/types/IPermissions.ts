// This file will store shared permission-related types and functions.

import { IOrg } from './IOrg'; // Assuming IOrg will also be in dashboard/types or similar

export type PremStatus = 'free' | 'pro' | string;

export interface OrgFeaturePermissions {
  tierName: PremStatus;
  projects: {
    canCreateMultiple: boolean;
    maxAllowed: number | null; // null for unlimited
  };
  usersAndOrgs: {
    canCreateMultipleOrgs: boolean;
    maxOrgsAllowed: number | null;
    maxSeatsPerOrg: number | null; // e.g., Free: 1, Pro: 10, Enterprise: null
    canInviteUsers: boolean;
  };
  dataAccess: {
    lookbackDays: {
      metrics: number;
      traces: number;
      logs: number;
    };
    spanWaterfallLimit: number | null;
    logLinesLimit: number | null;
    // True if user can see traces older than standard lookback (e.g. last 3 for free for specific cases)
    canViewAnyTraceAgeBeyondStandardLookback: boolean;
  };
  billingAndUsage: {
    maxSpansMonthly: number | null;
    canViewCostBreakdowns: boolean;
  };
  advancedFeatures: {
    hasAccessToEvals: boolean;
    hasAccessToNotifications: boolean;
    hasAccessToDataExports: boolean;
    canUseCustomAttributes: boolean;
    // Enterprise-specific example
    hasCustomSSO: boolean;
  };
}

// Define default permissions for each tier
export const defaultFreePermissions: OrgFeaturePermissions = {
  tierName: 'free',
  projects: { canCreateMultiple: false, maxAllowed: 1 },
  usersAndOrgs: {
    canCreateMultipleOrgs: false,
    maxOrgsAllowed: 1,
    maxSeatsPerOrg: 1,
    canInviteUsers: false,
  },
  dataAccess: {
    lookbackDays: { metrics: 30, traces: 3, logs: 3 },
    spanWaterfallLimit: 30,
    logLinesLimit: 100,
    canViewAnyTraceAgeBeyondStandardLookback: false,
  },
  billingAndUsage: { maxSpansMonthly: 5000, canViewCostBreakdowns: false },
  advancedFeatures: {
    hasAccessToEvals: false,
    hasAccessToNotifications: false,
    hasAccessToDataExports: false,
    canUseCustomAttributes: false,
    hasCustomSSO: false,
  },
};

export const defaultProPermissions: OrgFeaturePermissions = {
  ...defaultFreePermissions,
  tierName: 'pro',
  projects: {
    canCreateMultiple: true,
    maxAllowed: null, // null = unlimited projects
  },
  usersAndOrgs: {
    ...defaultFreePermissions.usersAndOrgs,
    maxSeatsPerOrg: null, // null = unlimited seats - update if plan breakdown changes
    canInviteUsers: true,
    canCreateMultipleOrgs: true,
    maxOrgsAllowed: null, // null = unlimited orgs - update if plan breakdown changes
  },
  dataAccess: {
    ...defaultFreePermissions.dataAccess,
    lookbackDays: {
      metrics: 365 * 10, // 10 years = effectively unlimited - update if plan breakdown changes
      traces: 365 * 10, // 10 years = effectively unlimited - update if plan breakdown changes
      logs: 365 * 10, // 10 years = effectively unlimited - update if plan breakdown changes
    },
    spanWaterfallLimit: null, // null = unlimited spans in waterfall
    logLinesLimit: null, // null = unlimited log lines
    canViewAnyTraceAgeBeyondStandardLookback: true,
  },
  billingAndUsage: {
    maxSpansMonthly: 100000, // 100k spans included per month
    canViewCostBreakdowns: true,
  },
  advancedFeatures: {
    ...defaultFreePermissions.advancedFeatures,
    hasAccessToEvals: true,
    hasAccessToNotifications: true,
    hasAccessToDataExports: true,
    canUseCustomAttributes: true,
  },
};

export const getDerivedPermissions = (orgData?: IOrg | null): OrgFeaturePermissions => {
  if (!orgData || !orgData.prem_status) {
    return defaultFreePermissions; // Fallback if no orgData or prem_status
  }

  let basePermissions: OrgFeaturePermissions;
  // Normalize the status to lowercase for comparison
  const status = (orgData.prem_status as string).toLowerCase() as PremStatus;

  switch (status) {
    case 'pro':
      basePermissions = defaultProPermissions;
      break;
    case 'free':
    default:
      basePermissions = defaultFreePermissions;
      break;
  }

  // Use object spread for a more efficient deep copy
  const derived: OrgFeaturePermissions = {
    ...basePermissions,
    tierName: orgData.prem_status as PremStatus,
    projects: { ...basePermissions.projects },
    usersAndOrgs: { ...basePermissions.usersAndOrgs },
    dataAccess: {
      ...basePermissions.dataAccess,
      lookbackDays: { ...basePermissions.dataAccess.lookbackDays },
    },
    billingAndUsage: { ...basePermissions.billingAndUsage },
    advancedFeatures: { ...basePermissions.advancedFeatures },
  };

  // Apply organization-specific overrides from orgData
  if (orgData.max_project_count !== undefined && orgData.max_project_count !== null) {
    derived.projects.maxAllowed =
      orgData.max_project_count === 0 ? null : orgData.max_project_count;
    derived.projects.canCreateMultiple =
      status !== 'free' ||
      (derived.projects.maxAllowed !== null && derived.projects.maxAllowed > 1) ||
      derived.projects.maxAllowed === null;
  } else if (status === 'free') {
    derived.projects.canCreateMultiple = false;
    derived.projects.maxAllowed = 1;
  }

  if (orgData.max_member_count !== undefined && orgData.max_member_count !== null) {
    derived.usersAndOrgs.maxSeatsPerOrg =
      orgData.max_member_count === 0 ? null : orgData.max_member_count;
    derived.usersAndOrgs.canInviteUsers =
      status !== 'free' ||
      (derived.usersAndOrgs.maxSeatsPerOrg !== null && derived.usersAndOrgs.maxSeatsPerOrg > 1) ||
      derived.usersAndOrgs.maxSeatsPerOrg === null;
  } else if (status === 'free') {
    derived.usersAndOrgs.canInviteUsers = false;
    derived.usersAndOrgs.maxSeatsPerOrg = 1;
  }

  // Add other specific overrides if necessary, for example, from a feature flags object in orgData
  // e.g. derived.advancedFeatures.hasAccessToEvals = orgData.feature_flags?.evals ?? basePermissions.advancedFeatures.hasAccessToEvals;

  return derived;
};
