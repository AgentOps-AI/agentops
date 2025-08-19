/// <reference types="cypress" />

/**
 * Tier Testing Utilities
 * Provides reusable functions and patterns for testing Free and Pro tier features
 */

export interface TierConfig {
  name: 'free' | 'pro';
  limits: {
    monthlySpans: number | null;
    maxProjects: number | null;
    maxOrganizations: number | null;
    maxSeatsPerOrg: number | null;
    traceLookbackDays: number | null;
    metricsLookbackDays: number | null;
    queryDateRangeDays: number | null;
    waterfallMaxSpans: number | null;
    maxLogLines: number | null;
  };
  features: {
    toolCosts: boolean;
    evaluations: boolean;
    notifications: boolean;
    dataExports: boolean;
    customAttributes: boolean;
    costBreakdowns: boolean;
  };
  ui: {
    sidebarBadge: string;
    showSpanUsage: boolean;
    showUpgradePrompts: boolean;
    datePickerRestricted: boolean;
    logsUpgradeButton: boolean;
    tracesTimeoutIcon: boolean;
  };
}

export const TIER_CONFIGS: Record<'free' | 'pro', TierConfig> = {
  free: {
    name: 'free',
    limits: {
      monthlySpans: 5000,
      maxProjects: 1,
      maxOrganizations: 1,
      maxSeatsPerOrg: 1,
      traceLookbackDays: 3,
      metricsLookbackDays: 30,
      queryDateRangeDays: 7,
      waterfallMaxSpans: 30,
      maxLogLines: 100,
    },
    features: {
      toolCosts: false,
      evaluations: false,
      notifications: false,
      dataExports: false,
      customAttributes: false,
      costBreakdowns: false,
    },
    ui: {
      sidebarBadge: 'Hobby Plan',
      showSpanUsage: true,
      showUpgradePrompts: true,
      datePickerRestricted: true,
      logsUpgradeButton: true,
      tracesTimeoutIcon: true,
    },
  },
  pro: {
    name: 'pro',
    limits: {
      monthlySpans: 100000, // 100k included
      maxProjects: null,
      maxOrganizations: null,
      maxSeatsPerOrg: null,
      traceLookbackDays: null,
      metricsLookbackDays: null,
      queryDateRangeDays: null,
      waterfallMaxSpans: null,
      maxLogLines: null,
    },
    features: {
      toolCosts: true,
      evaluations: true,
      notifications: true,
      dataExports: true,
      customAttributes: true,
      costBreakdowns: true,
    },
    ui: {
      sidebarBadge: 'Pro',
      showSpanUsage: false,
      showUpgradePrompts: false,
      datePickerRestricted: false,
      logsUpgradeButton: false,
      tracesTimeoutIcon: false,
    },
  },
};

/**
 * Sets up the test environment for a specific tier
 * @param tier The tier to set up ('free' or 'pro')
 */
export function setupTierEnvironment(tier: 'free' | 'pro') {
  const config = TIER_CONFIGS[tier];

  // Mock the organization API response based on tier
  cy.intercept('GET', '/api/organizations/*', {
    statusCode: 200,
    body: {
      ...cy.fixture(`org-${tier}-tier.json`),
      prem_status: tier,
    },
  }).as('getOrganization');

  // Mock user permissions based on tier
  cy.intercept('GET', '/api/auth/session', {
    statusCode: 200,
    body: {
      user: {
        email: 'test@example.com',
        name: 'Test User',
        image: null,
      },
      expires: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    },
  }).as('getSession');

  return config;
}

// Export custom Cypress commands for tier testing
declare global {
  namespace Cypress {
    interface Chainable {
      setupTier(tier: 'free' | 'pro'): Chainable<TierConfig>;
      assertTierLimit(feature: string, tier: 'free' | 'pro'): Chainable<void>;
    }
  }
}

// Add custom commands
Cypress.Commands.add('setupTier', (tier: 'free' | 'pro') => {
  return cy.wrap(setupTierEnvironment(tier));
});

Cypress.Commands.add('assertTierLimit', (feature: string, tier: 'free' | 'pro') => {
  const config = TIER_CONFIGS[tier];
  cy.log(`Asserting ${feature} limit for ${tier} tier`);
  // Implementation depends on specific feature
});
