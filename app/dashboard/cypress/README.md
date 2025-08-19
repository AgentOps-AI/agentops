# Cypress End-to-End Testing 🧪

This directory contains the End-to-End (E2E) tests for the dashboard, powered by [Cypress](https://www.cypress.io/).

> **Note:** For setup, environment variables, and running instructions, refer to the [main project README](../../README.md) and [dashboard README](../../dashboard/README.md). This file only covers dashboard-specific conventions and notes.

## Notes for CI & Test Maintenance

- Some tests may be disabled (e.g., duplicate project prevention) if backend support is not present. These are clearly marked in the code and should not affect CI stability.
- All comments in test files should be concise and only included when necessary for clarity. Avoid verbose or redundant comments.

## Data-testid Convention 🏷️

To ensure tests are readable and resilient to code changes, we use a consistent naming convention for `data-testid` attributes on interactive elements.

The pattern is:

`data-testid="[component-name]-[element-type]-[description]"`

- **`[component-name]`**: The logical name of the component the element belongs to (e.g., `login-form`, `project-card`, `header-menu`).
- **`[element-type]`**: The type or role of the element (e.g., `input`, `button`, `link`, `error-message`, `title`).
- **`[description]`**: A brief, specific description of the element's purpose (e.g., `email`, `submit`, `view-details`, `invalid-credentials`, `user-avatar`).

**Examples:**

```html
<input data-testid="login-form-input-email" ... />
<button data-testid="login-form-button-submit" ...>Login</button>
<p data-testid="project-card-error-message-fetch-failed">Failed to load projects.</p>
<a data-testid="header-menu-link-settings" ...>Settings</a>
```

Using this convention makes it easier to identify elements in tests and understand their context within the application.
_(Or `npm run dev` if you use npm)_

**Terminal 2: Run Cypress** 🌲

Open the interactive Cypress Test Runner:

```bash
bun run cy:open
```

_(Or `npm run cy:open` if you use npm)_

This will open the Cypress application, where you can see all the spec files (`*.cy.ts`) and run them individually or all together in your browser.

**Headless Mode (for CI/CD or background runs):**

To run all tests headlessly (without the UI) in the terminal:

```bash
bun run cy:run
# or
npm run cy:run
```

## Implicit Assertions & Avoiding `cy.wait()` ⏳

Cypress commands like `cy.get()`, `find()`, and assertion commands (`.should()`, `.click()`, etc.) have **built-in retry mechanisms**. They automatically wait for the element to exist in the DOM and reach an actionable state before proceeding or timing out.

**`cy.get()` is an assertion:** When you write `cy.get('[data-testid="login-form-button-submit"]')`, Cypress automatically retries finding this element for a default timeout period (usually 4 seconds). If the element doesn't appear within that time, the test fails. This means `cy.get()` _implicitly asserts_ that the element exists.

**Therefore, you should almost never use arbitrary waits like `cy.wait(1000)` just to wait for an element to appear.**

Instead, rely on Cypress commands to wait for the specific condition you need:

- **Waiting for an element:** Use `cy.get('selector')` or `cy.contains('text')`.
- **Waiting for an element to be visible/actionable:** Use `cy.get('selector').should('be.visible')` or directly chain actions like `.click()`. Cypress waits for the element to be ready before performing the action.
- **Waiting for a network request:** Use `cy.intercept()` to define the request and `cy.wait('@alias')` to wait for that specific network call to complete.

Using Cypress's built-in waits leads to faster, more reliable, and less flaky tests compared to fixed-time waits.

## Code Coverage (Future) 🚧

Instrumentation for code coverage reporting is currently disabled due to conflicts with Next.js/Turbopack. This will be revisited.

When enabled, you would typically run:

```bash
# Terminal 1 (Server with instrumentation - requires specific setup)
# bun run dev:cy

# Terminal 2 (Run tests and collect coverage)
# bun run cy:run:coverage
```

## File Structure 📁

- `cypress/`
  - `e2e/`: Contains the actual test files (specs), often organized by feature (e.g., `auth/login.cy.ts`).
  - `fixtures/`: Holds static data (like JSON) that can be used in tests (e.g., `cy.fixture('user')`).
  - `screenshots/`: Default location for screenshots taken during test failures or manually.
  - `support/`: Contains configuration and utility files for Cypress.
    - `e2e.ts`: Runs before every spec file. Good place for global setup like the `uncaught:exception` handler.
    - `commands.ts`: Define custom Cypress commands (e.g., `cy.login()`).
  - `videos/`: Default location for videos recorded during `cypress run`.
- `cypress.config.ts`: The main Cypress configuration file (baseUrl, env variables, etc.).

Happy Testing! 😊
