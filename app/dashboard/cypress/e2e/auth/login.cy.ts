/// <reference types="cypress" />

/**
 * E2E: Login Flow
 * Verifies that a user can log in using the custom Cypress command.
 */
describe('Login Flow', () => {
  it('successfully logs in a user', () => {
    cy.login();
  });

  it('shows an error message for invalid credentials', () => {
    cy.visit('/');
    cy.getDataTestId('signin-page-container', { timeout: 10000 }).should('be.visible');

    // Mock the API to return a 401 or specific error for bad credentials
    cy.intercept('POST', '**/auth/login', {
      statusCode: 401,
      body: { error: 'Invalid credentials' },
    }).as('failedLoginRequest');

    cy.getDataTestId('login-form-input-email')
      .should('be.visible')
      .clear()
      .type('wrong@example.com');
    cy.getDataTestId('login-form-input-password')
      .should('be.visible')
      .clear()
      .type('wrongpassword');
    cy.getDataTestId('login-form-button-submit').should('be.visible').click();

    cy.wait('@failedLoginRequest');

    cy.assertToastMessage(
      'Oops, something is preventing Agent YOU 🫵 from logging in, please try again or contact support',
      'destructive',
    );
    cy.url().should('include', '/signin');
  });

  it('shows a generic error message for a server error during login', () => {
    cy.visit('/');
    cy.getDataTestId('signin-page-container', { timeout: 10000 }).should('be.visible');

    cy.intercept('POST', '**/auth/login', {
      statusCode: 500,
      body: { error: 'Internal Server Error' },
    }).as('serverErrorLoginRequest');

    const username = Cypress.env('CYPRESS_USER');
    const password = Cypress.env('CYPRESS_PASSWORD');

    cy.getDataTestId('login-form-input-email').should('be.visible').clear().type(username);
    cy.getDataTestId('login-form-input-password').should('be.visible').clear().type(password);
    cy.getDataTestId('login-form-button-submit').should('be.visible').click();

    cy.wait('@serverErrorLoginRequest');

    cy.assertToastMessage(
      'Oops, something is preventing Agent YOU 🫵 from logging in, please try again or contact support',
      'destructive',
    );
    cy.url().should('include', '/signin');
  });

  it('shows an error message if the login API call fails (network error)', () => {
    cy.visit('/');
    cy.getDataTestId('signin-page-container', { timeout: 10000 }).should('be.visible');

    cy.intercept('POST', '**/auth/login', {
      forceNetworkError: true,
    }).as('networkErrorLoginRequest');

    const username = Cypress.env('CYPRESS_USER');
    const password = Cypress.env('CYPRESS_PASSWORD');

    cy.getDataTestId('login-form-input-email').should('be.visible').clear().type(username);
    cy.getDataTestId('login-form-input-password').should('be.visible').clear().type(password);
    cy.getDataTestId('login-form-button-submit').should('be.visible').click();

    cy.wait('@networkErrorLoginRequest');

    cy.assertToastMessage(
      'Oops, something is preventing Agent YOU 🫵 from logging in, please try again or contact support',
      'destructive',
    );
    cy.url().should('include', '/signin');
  });
});
