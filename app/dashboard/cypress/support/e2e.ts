// ***********************************************************
// This example support/e2e.ts is processed and
// loaded automatically before your test files.
//
// This is a great place to put global configuration and
// behavior that modifies Cypress.
//
// You can change the location of this file or turn off
// automatically serving support files with the
// 'supportFile' configuration option.
//
// You can read more here:
// https://on.cypress.io/configuration
// ***********************************************************

// Import commands.js using ES2015 syntax:
import './commands';
// import './utils'; // No longer needed
import './tier-testing'; // Import tier testing utilities
import '@cypress/code-coverage/support';

// Ignore specific Next.js redirect errors
Cypress.on('uncaught:exception', (err) => {
  // Check if the error is the specific NEXT_REDIRECT error
  // Next.js throws this error internally for redirects
  if (err.message.includes('NEXT_REDIRECT')) {
    // Returning false here prevents Cypress from failing the test
    return false;
  }
  // Allow other uncaught exceptions to fail the test
  return true;
});
