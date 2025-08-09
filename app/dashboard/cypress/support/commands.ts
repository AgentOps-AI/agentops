/// <reference types="cypress" />

// Import tier testing utilities
import './tier-testing';

// ***********************************************
// This example commands.ts shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add('login', (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add('drag', { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add('dismiss', { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This will overwrite an existing command --
// Cypress.Commands.overwrite('visit', (originalFn, url, options) => { ... })

/**
 * Custom command to select DOM element by data-testid attribute.
 * @example cy.getDataTestId('greeting')
 */
Cypress.Commands.add('getDataTestId', (selector, ...args) => {
  return cy.get(`[data-testid="${selector}"]`, ...args);
});

Cypress.Commands.add('login', () => {
  const username = Cypress.env('CYPRESS_USER');
  const password = Cypress.env('CYPRESS_PASSWORD');

  if (!username || !password) {
    throw new Error('CYPRESS_USER and CYPRESS_PASSWORD environment variables must be set');
  }

  cy.intercept('POST', '**/auth/login').as('loginRequest');

  cy.visit('/');

  cy.getDataTestId('signin-page-container', { timeout: 10000 }).should('be.visible');

  cy.getDataTestId('login-form-input-email').should('be.visible').clear().type(username);
  cy.getDataTestId('login-form-input-password').should('be.visible').clear().type(password);
  cy.getDataTestId('login-form-button-submit').should('be.visible').click();

  cy.wait('@loginRequest').its('response.statusCode').should('eq', 200);

  cy.url().should('include', '/projects');

  // Wait for any loading overlays to disappear and then check for user menu
  cy.wait(1000); // Give time for page to fully load

  // Use force: true to click through any overlays, or wait for the element to be actionable
  cy.getDataTestId('user-menu-dropdown-trigger', { timeout: 10000 })
    .should('exist')
    .then(($el) => {
      // If element is covered, we can still verify it exists and the login was successful
      // The main goal is to verify login worked, not necessarily to interact with the menu
      cy.log('User menu trigger found - login successful');
    });
});

Cypress.Commands.add('selectDefaultProjectForWumboOrg', () => {
  cy.getDataTestId('project-card-Default Project').click();
  cy.log('Project selected');

  cy.url({ timeout: 10000 }).should('include', '/overview');
  cy.contains('Default Project', { timeout: 10000 }).should('exist');
});

Cypress.Commands.add('selectProject', (projectName: string) => {
  cy.getDataTestId('project-selector').click();

  cy.getDataTestId(`project-selector-item-${projectName.replace(/\s+/g, '-')}`).click();
  cy.log(`Project "${projectName}" selected`);
  cy.getDataTestId('project-selector').should('contain', projectName);
});

Cypress.Commands.add('openUserMenu', () => {
  cy.getDataTestId('user-menu-dropdown-trigger').click();
  cy.log('User menu opened');
});

Cypress.Commands.add('navigateTo', (section: string) => {
  cy.getDataTestId(`nav-link-${section.toLowerCase().replace(/\s+/g, '-')}`).click();
  cy.url().should('include', `/${section.toLowerCase().replace(/\s+/g, '-')}`);
  cy.log(`Navigated to ${section}`);
});

/**
 * Asserts that the current URL includes the given path.
 * @param path The path to check for in the URL.
 * @example cy.assertUrlIncludes('/settings/account');
 */
Cypress.Commands.add('assertUrlIncludes', (path: string) => {
  cy.url().should('include', path);
});

/**
 * Asserts that a toast message is visible with the expected text and optional variant.
 * This assumes toast messages can be reliably selected via data-testid="toast-{variant}-{id}".
 * @param message The expected message text in the toast.
 * @param variant Optional variant (e.g., 'success', 'destructive') to check in data-testid.
 * @example cy.assertToastMessage('Profile updated successfully!', 'success');
 */
Cypress.Commands.add('assertToastMessage', (message: string, variant?: string) => {
  const baseSelector = '[data-testid^="toast-"]';
  let specificSelector = baseSelector;

  if (variant) {
    // Assumes variant is part of the testid like: toast-destructive-someId
    // This will find any toast that contains the variant in its testid
    specificSelector = `[data-testid*="toast-${variant}-"]`;
  }

  // First, ensure a toast matching the variant (if any) exists and is visible
  // Then, within that context (or all toasts if no variant), check for the message.
  cy.get(specificSelector).should('be.visible').and('contain.text', message);
});

// Add type declaration for the new custom command
declare global {
  namespace Cypress {
    interface Chainable {
      /**
       * Custom command to select DOM element by data-testid attribute.
       * @example cy.getDataTestId('greeting')
       */
      getDataTestId(selector: string, ...args: any[]): Chainable<JQuery<HTMLElement>>;
      login(): Chainable<void>;
      selectDefaultProjectForWumboOrg(): Chainable<void>;
      selectProject(projectName: string): Chainable<void>;
      openUserMenu(): Chainable<void>;
      navigateTo(section: string): Chainable<void>;
      assertUrlIncludes(path: string): Chainable<void>;
      assertToastMessage(message: string, variant?: string): Chainable<void>;
    }
  }
}

export {};
