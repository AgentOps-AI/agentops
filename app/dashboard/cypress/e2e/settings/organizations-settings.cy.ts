/// <reference types="cypress" />

/**
 * E2E: Organizations Settings
 * Tests organization management functionality
 * Note: Tier-specific behavior will be tested when tier setup is properly implemented
 */
describe('Settings - Organizations', () => {
  beforeEach(() => {
    cy.login();
  });

  it('should display organizations settings page correctly', () => {
    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'free',
          current_user_role: 'owner',
        },
      ],
    }).as('getOrgs');

    cy.intercept('GET', '**/opsboard/orgs/invites', {
      statusCode: 200,
      body: [],
    }).as('getInvites');

    cy.visit('/settings/organizations');
    cy.wait(['@getOrgs', '@getInvites']);

    cy.getDataTestId('organizations-settings-header')
      .should('be.visible')
      .and('contain', 'Organizations');

    cy.getDataTestId('org-settings-membership-card').should('be.visible');
  });

  it('should display organization members correctly', () => {
    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'free',
          current_user_role: 'owner',
        },
        {
          id: 'org-2',
          name: 'Second Organization',
          prem_status: 'pro',
          current_user_role: 'member',
        },
      ],
    }).as('getOrgsWithMultiple');

    cy.intercept('GET', '**/opsboard/orgs/invites', {
      statusCode: 200,
      body: [],
    }).as('getInvites');

    cy.visit('/settings/organizations');
    cy.wait(['@getOrgsWithMultiple', '@getInvites']);

    cy.getDataTestId('org-settings-membership-card').within(() => {
      cy.getDataTestId('org-settings-membership-row-org-1').should('contain', 'Test Organization');

      cy.getDataTestId('org-settings-membership-row-org-2').should(
        'contain',
        'Second Organization',
      );
    });
  });

  it('should navigate to organization detail page', () => {
    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'free',
          current_user_role: 'owner',
        },
      ],
    }).as('getOrgs');

    cy.intercept('GET', '**/opsboard/orgs/invites', {
      statusCode: 200,
      body: [],
    }).as('getInvites');

    cy.visit('/settings/organizations');
    cy.wait(['@getOrgs', '@getInvites']);

    cy.getDataTestId('org-settings-membership-button-manage-org-1').click();

    cy.url().should('include', '/settings/organizations/org-1');
  });

  it('should handle accepting invitations', () => {
    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [],
    }).as('getOrgsEmpty');

    cy.intercept('GET', '**/opsboard/orgs/invites', {
      statusCode: 200,
      body: [
        {
          user_id: 'user-1',
          org_id: 'org-2',
          role: 'developer',
          org_name: 'Inviting Organization',
          inviter: 'inviter@example.com',
        },
      ],
    }).as('getInvitesWithPending');

    cy.visit('/settings/organizations');
    cy.wait(['@getOrgsEmpty', '@getInvitesWithPending']);

    cy.getDataTestId('org-settings-invitations-card').should('be.visible');
    cy.getDataTestId('org-settings-invitation-row-org-2')
      .should('contain', 'Inviting Organization')
      .and('contain', 'inviter@example.com')
      .and('contain', 'Developer');

    cy.intercept('POST', '**/opsboard/orgs/org-2/accept', {
      statusCode: 200,
      body: { success: true },
    }).as('acceptInvite');

    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [
        {
          id: 'org-2',
          name: 'Inviting Organization',
          prem_status: 'free',
          current_user_role: 'developer',
        },
      ],
    }).as('getOrgsAfterAccept');

    cy.intercept('GET', '**/opsboard/orgs/invites', {
      statusCode: 200,
      body: [],
    }).as('getInvitesAfterAccept');

    cy.getDataTestId('org-settings-invitation-button-accept-org-2').click();

    cy.wait('@acceptInvite');

    cy.get('[data-testid^="toast-default-"]')
      .should('be.visible')
      .and('contain.text', 'Organization Successfully Joined!');
  });

  it('should show create new organization button', () => {
    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'free',
          current_user_role: 'owner',
        },
      ],
    }).as('getOrgs');

    cy.intercept('GET', '**/opsboard/orgs/invites', {
      statusCode: 200,
      body: [],
    }).as('getInvites');

    cy.visit('/settings/organizations');
    cy.wait(['@getOrgs', '@getInvites']);

    cy.wait(500);

    cy.get(
      '[data-testid="org-settings-membership-button-create-new-org-trigger"], [data-testid="org-settings-membership-tooltip-create-new-org-trigger"]',
    ).should('exist');
  });

  it('should handle API errors gracefully', () => {
    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 500,
      body: {
        error: 'Failed to load organizations',
      },
    }).as('getOrgsError');

    cy.intercept('GET', '**/opsboard/orgs/invites', {
      statusCode: 500,
      body: {
        error: 'Failed to load invites',
      },
    }).as('getInvitesError');

    cy.visit('/settings/organizations');
    cy.wait(['@getOrgsError', '@getInvitesError']);

    cy.getDataTestId('organizations-settings-header').should('be.visible');

    cy.contains('Manage your organizations, members, and pending invitations.').should(
      'be.visible',
    );
  });
});
