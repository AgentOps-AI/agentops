/// <reference types="cypress" />

/**
 * E2E: Empty Traces List for Default Project
 * Validates that the traces page shows an empty state when no traces exist for the default project.
 */
describe('Traces: Empty Default Project', () => {
  before(() => {
    cy.login();
    cy.selectDefaultProjectForWumboOrg();
  });

  it('displays empty state when no traces exist for the default project', () => {
    cy.visit('/traces');

    // Wait for the page to load and check for empty state
    // This assumes that the default project has no traces
    // If traces exist, this test might need to be adjusted or run in a clean environment

    // Check for empty state message or component
    // The exact selector depends on your empty state implementation
    cy.getDataTestId('traces-list-empty-state').should('be.visible');

    // Additional checks for empty state content
    // cy.contains('No traces found').should('be.visible');
    // cy.contains('Start sending traces').should('be.visible');

    // Verify that no trace rows are displayed
    // cy.getDataTestId('trace-row').should('not.exist');
  });
});
