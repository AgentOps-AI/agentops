/// <reference types="cypress" />

/**
 * E2E: Billing Settings
 * Tests billing management functionality
 * Note: Tier-specific behavior will be tested when tier setup is properly implemented
 */
describe('Settings - Billing', () => {
  beforeEach(() => {
    // Prevent Stripe errors from failing tests
    cy.on('uncaught:exception', (err) => {
      if (err.message.includes('payment_page') || err.message.includes('Stripe')) {
        return false;
      }
    });

    cy.login();
    cy.visit('/settings/organization');
  });

  it('should display billing settings page correctly', () => {
    cy.getDataTestId('billing-settings-header').should('be.visible').and('contain', 'Billing');

    cy.getDataTestId('billing-org-list').should('be.visible');
  });

  it('should display organizations with correct plan status', () => {
    cy.intercept('GET', '**/opsboard/orgs*', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'free',
          current_user_role: 'owner',
          created_at: new Date().toISOString(),
        },
      ],
    }).as('getOrganizations');

    cy.visit('/settings/organization');
    cy.wait('@getOrganizations');

    cy.getDataTestId('billing-org-item-org-1').should('be.visible');
    cy.getDataTestId('billing-org-item-name-org-1').should('contain', 'Test Organization');
    cy.getDataTestId('billing-org-item-plan-status-org-1').should('contain', 'Free Plan');
  });

  it('should show upgrade button for free tier organizations', () => {
    cy.intercept('GET', '**/opsboard/orgs*', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'free',
          current_user_role: 'owner',
          created_at: new Date().toISOString(),
        },
      ],
    }).as('getOrganizations');

    cy.visit('/settings/organization');
    cy.wait('@getOrganizations');

    cy.getDataTestId('billing-org-item-button-upgrade-org-1')
      .should('be.visible')
      .and('contain', 'Upgrade to Premium');
  });

  it('should handle upgrade flow', () => {
    cy.intercept('GET', '**/opsboard/orgs*', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'free',
          current_user_role: 'owner',
          created_at: new Date().toISOString(),
        },
      ],
    }).as('getOrganizations');

    cy.intercept('POST', '**/opsboard/orgs/org-1/create-checkout-session', {
      statusCode: 200,
      body: {
        clientSecret: 'cs_test_a1234567890abcdef_secret_1234567890abcdef',
      },
      delay: 500,
    }).as('createCheckout');

    cy.visit('/settings/organization');
    cy.wait('@getOrganizations');

    cy.getDataTestId('billing-org-item-button-upgrade-org-1').click();

    cy.getDataTestId('billing-checkout-dialog-content').should('be.visible');
    cy.getDataTestId('billing-checkout-dialog-title').should('contain', 'Upgrade Plan');

    cy.getDataTestId('billing-checkout-dialog-loader').should('be.visible');

    cy.wait('@createCheckout');

    cy.getDataTestId('billing-checkout-dialog-loader').should('not.exist');

    cy.getDataTestId('billing-checkout-dialog-button-cancel').should('be.visible');

    cy.getDataTestId('billing-checkout-dialog-button-cancel').click();
    cy.getDataTestId('billing-checkout-dialog-content').should('not.exist');
  });

  it('should handle payment form interaction', () => {
    cy.intercept('GET', '**/opsboard/orgs*', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'free',
          current_user_role: 'owner',
          created_at: new Date().toISOString(),
        },
      ],
    }).as('getOrganizations');

    cy.intercept('POST', '**/opsboard/orgs/org-1/create-checkout-session', {
      statusCode: 200,
      body: {
        clientSecret: 'cs_test_a1234567890abcdef_secret_1234567890abcdef',
      },
    }).as('createCheckout');

    cy.visit('/settings/organization');
    cy.wait('@getOrganizations');

    cy.getDataTestId('billing-org-item-button-upgrade-org-1').click();
    cy.wait('@createCheckout');

    cy.getDataTestId('billing-checkout-dialog-content').within(() => {
      cy.getDataTestId('billing-checkout-dialog-title').should('be.visible');
      cy.getDataTestId('billing-checkout-dialog-description').should('be.visible');

      cy.getDataTestId('billing-checkout-dialog-button-cancel').should('be.visible');
    });

    cy.getDataTestId('billing-checkout-dialog-button-cancel').click();
    cy.getDataTestId('billing-checkout-dialog-content').should('not.exist');
  });

  it('should show cancel subscription button for premium organizations', () => {
    cy.intercept('GET', '**/opsboard/orgs*', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'pro',
          current_user_role: 'owner',
          subscription_id: 'sub_123',
          created_at: new Date().toISOString(),
        },
      ],
    }).as('getOrganizations');

    cy.visit('/settings/organization');
    cy.wait('@getOrganizations');

    cy.getDataTestId('billing-org-item-plan-status-org-1').should('contain', 'Premium');

    cy.getDataTestId('billing-org-item-button-cancel-sub-trigger-org-1')
      .should('be.visible')
      .and('contain', 'Cancel Subscription');
  });

  it('should handle cancel subscription flow', () => {
    cy.intercept('GET', '**/opsboard/orgs*', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'pro',
          current_user_role: 'owner',
          subscription_id: 'sub_123',
          created_at: new Date().toISOString(),
        },
      ],
    }).as('getOrganizations');

    cy.intercept('POST', '**/opsboard/orgs/org-1/cancel-subscription', {
      statusCode: 200,
      body: {
        success: true,
        message: 'Subscription will be cancelled at end of billing period',
      },
    }).as('cancelSubscription');

    cy.visit('/settings/organization');
    cy.wait('@getOrganizations');

    cy.getDataTestId('billing-org-item-button-cancel-sub-trigger-org-1').click();

    cy.getDataTestId('billing-org-item-dialog-cancel-sub-content-org-1').should('be.visible');

    cy.getDataTestId('billing-org-item-dialog-button-confirm-cancel-org-1').click();

    cy.wait('@cancelSubscription');

    cy.getDataTestId('billing-response-dialog-content').should('be.visible');
    cy.getDataTestId('billing-response-dialog-title').should('contain', 'Subscription Cancelled');

    cy.getDataTestId('billing-response-dialog-button-ok').click();
    cy.getDataTestId('billing-response-dialog-content').should('not.exist');
  });

  it('should handle billing API errors gracefully', () => {
    cy.intercept('GET', '**/opsboard/orgs*', {
      statusCode: 500,
      body: {
        error: 'Failed to load organizations',
      },
    }).as('getOrganizationsError');

    cy.visit('/settings/organization');
    cy.wait('@getOrganizationsError');

    cy.getDataTestId('billing-settings-header').should('be.visible');
    cy.get('body').should('contain', 'Billing');
  });

  it('should handle checkout session errors', () => {
    cy.intercept('GET', '**/opsboard/orgs*', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'free',
          current_user_role: 'owner',
          created_at: new Date().toISOString(),
        },
      ],
    }).as('getOrganizations');

    cy.intercept('POST', '**/opsboard/orgs/org-1/create-checkout-session', {
      statusCode: 500,
      body: {
        error: 'Failed to create checkout session',
      },
    }).as('createCheckoutError');

    cy.visit('/settings/organization');
    cy.wait('@getOrganizations');

    cy.getDataTestId('billing-org-item-button-upgrade-org-1').click();

    cy.wait('@createCheckoutError');

    cy.getDataTestId('billing-response-dialog-content').should('be.visible');
    cy.getDataTestId('billing-response-dialog-title').should('contain', 'Checkout Error');

    cy.getDataTestId('billing-response-dialog-button-ok').click();

    cy.getDataTestId('billing-response-dialog-content').should('not.exist');
    cy.getDataTestId('billing-checkout-dialog-content').should('not.exist');
  });

  it('should not show action buttons for non-admin users', () => {
    cy.intercept('GET', '**/opsboard/orgs*', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'free',
          current_user_role: 'member',
          created_at: new Date().toISOString(),
        },
      ],
    }).as('getOrganizations');

    cy.visit('/settings/organization');
    cy.wait('@getOrganizations');

    cy.getDataTestId('billing-org-item-button-upgrade-org-1').should('not.exist');
  });
});
