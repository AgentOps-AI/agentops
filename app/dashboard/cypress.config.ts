import { defineConfig } from 'cypress';
import codeCoverageTask from '@cypress/code-coverage/task';
import * as dotenv from 'dotenv';

dotenv.config();

export default defineConfig({
  video: true,
  viewportWidth: 1920,
  viewportHeight: 1080,
  reporter: 'cypress-mochawesome-reporter',
  reporterOptions: {
    reportDir: 'cypress/reports/html',
    charts: true,
    reportPageTitle: 'Cypress Test Report',
    embeddedScreenshots: true,
    inlineAssets: true,
    saveAllAttempts: true,
    quiet: false,
  },
  // Add the env object to pass variables to Cypress tests
  env: {
    CYPRESS_USER: process.env.CYPRESS_USER,
    CYPRESS_PASSWORD: process.env.CYPRESS_PASSWORD,
    // Add other .env variables you need in tests here
  },
  e2e: {
    baseUrl: 'http://localhost:3000', // Set your dev server URL here
    defaultCommandTimeout: 5000,
    setupNodeEvents(on, config) {
      // Load environment variables from .env file into config.env
      // This makes them available via Cypress.env() in tests
      config.env.CYPRESS_USER = process.env.CYPRESS_USER;
      config.env.CYPRESS_PASSWORD = process.env.CYPRESS_PASSWORD;

      require('cypress-mochawesome-reporter/plugin')(on);
      codeCoverageTask(on, config);
      return config;
    },
  },
});
