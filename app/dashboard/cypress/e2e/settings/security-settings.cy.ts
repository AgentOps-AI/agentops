/// <reference types="cypress" />

/**
 * E2E: Security Settings
 * Tests security settings page
 * No tier-specific behavior - same for all users
 */
describe('Settings - Security', () => {
  beforeEach(() => {
    cy.login();
    cy.visit('/settings/security');
  });

  it('should display security settings page correctly', () => {
    cy.getDataTestId('security-settings-header').should('be.visible').and('contain', 'Security');
  });
});
