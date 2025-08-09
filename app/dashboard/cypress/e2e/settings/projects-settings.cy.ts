/// <reference types="cypress" />

/**
 * E2E: Projects & API Keys Settings
 * Tests project and API key management
 * Note: Tier-specific behavior will be tested when tier setup is properly implemented
 */
describe('Settings - Projects & API Keys', () => {
  beforeEach(() => {
    cy.login();
  });

  it('should display projects settings page correctly', () => {
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
    }).as('loadOrgsData');

    cy.intercept('GET', '**/opsboard/projects', {
      statusCode: 200,
      body: [],
    }).as('loadProjectsData');

    cy.visit('/settings/projects');
    cy.wait('@loadOrgsData');

    cy.getDataTestId('projects-settings-header')
      .should('be.visible')
      .and('contain', 'Projects & API Keys');
  });

  it('should display projects and API keys', () => {
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
    }).as('loadOrgsData');

    cy.intercept('GET', '**/opsboard/projects', {
      statusCode: 200,
      body: [
        {
          id: 'project-1',
          name: 'Test Project',
          api_key: 'agentops-api-key-123456789',
          created_at: new Date().toISOString(),
          org: { id: 'org-1', name: 'Test Organization' },
        },
      ],
    }).as('loadProjectsData');

    cy.visit('/settings/projects');
    cy.wait(['@loadOrgsData', '@loadProjectsData']);

    cy.wait(500);

    cy.getDataTestId('project-row').should('contain', 'Test Project');

    cy.getDataTestId('apikey-box-input')
      .last()
      .should('have.attr', 'type', 'text')
      .and('have.value', '••••••••••••••••••••••••••••23456789');
  });

  it('should toggle API key visibility', () => {
    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          current_user_role: 'owner',
        },
      ],
    }).as('loadOrgsData');

    cy.intercept('GET', '**/opsboard/projects', {
      statusCode: 200,
      body: [
        {
          id: 'project-1',
          name: 'Test Project',
          api_key: 'agentops-api-key-123456789',
          created_at: new Date().toISOString(),
          org: { id: 'org-1', name: 'Test Organization' },
        },
      ],
    }).as('loadProjectsData');

    cy.visit('/settings/projects');
    cy.wait(['@loadOrgsData', '@loadProjectsData']);

    cy.wait(500);

    cy.getDataTestId('apikey-box-button-toggle-visibility').last().click();

    cy.getDataTestId('apikey-box-input')
      .last()
      .should('have.attr', 'type', 'text')
      .and('have.value', 'agentops-api-key-123456789');

    cy.getDataTestId('apikey-box-button-toggle-visibility').last().click();

    cy.getDataTestId('apikey-box-input').last().should('have.attr', 'type', 'text');
  });

  it('should handle creating new projects', () => {
    const newProjectName = `Test Project ${Date.now()}`;

    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'pro',
          current_user_role: 'owner',
        },
      ],
    }).as('loadOrgsData');

    cy.intercept('GET', '**/opsboard/projects', {
      statusCode: 200,
      body: [],
    }).as('loadProjectsData');

    cy.intercept('POST', '**/opsboard/projects', {
      statusCode: 201,
      body: {
        id: 'project-2',
        name: newProjectName,
        api_key: 'new-api-key-456',
        created_at: new Date().toISOString(),
        org: { id: 'org-1', name: 'Test Organization' },
      },
    }).as('createProject');

    cy.visit('/settings/projects');
    cy.wait(['@loadOrgsData', '@loadProjectsData']);

    cy.getDataTestId('projects-settings-button-create-new-project-org-1').click();

    cy.getDataTestId('new-project-input').last().clear().type(newProjectName);
    cy.getDataTestId('create-project-confirm').last().click();

    cy.wait('@createProject');

    cy.get('[data-testid^="toast-default-"]')
      .should('be.visible')
      .and('contain.text', 'API Key Copied');
  });

  it('should handle rotating API keys', () => {
    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          current_user_role: 'owner',
        },
      ],
    }).as('loadOrgsData');

    cy.intercept('GET', '**/opsboard/projects', {
      statusCode: 200,
      body: [
        {
          id: 'project-1',
          name: 'Test Project',
          api_key: 'old-api-key-123456789',
          org: { id: 'org-1', name: 'Test Organization' },
        },
      ],
    }).as('loadProjectsData');

    cy.intercept('POST', '**/opsboard/projects/project-1/regenerate-key', {
      statusCode: 200,
      body: {
        id: 'project-1',
        name: 'Test Project',
        api_key: 'new-rotated-key-987654321',
        org: { id: 'org-1', name: 'Test Organization' },
      },
    }).as('rotateApiKey');

    cy.visit('/settings/projects');
    cy.wait(['@loadOrgsData', '@loadProjectsData']);

    cy.wait(500);

    cy.getDataTestId('project-row')
      .last()
      .within(() => {
        cy.get('svg').eq(3).click();
      });

    cy.get('[role="dialog"]').should('be.visible');
    cy.contains('button', 'Rotate API Key').click();

    cy.wait('@rotateApiKey');

    cy.get('[data-testid^="toast-default-"]')
      .should('be.visible')
      .and('contain.text', 'API Key Rotated Successfully');
  });

  it('should handle deleting projects', () => {
    const projectToDelete = 'Project to Delete';

    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          current_user_role: 'owner',
        },
      ],
    }).as('loadOrgsData');

    cy.intercept('GET', '**/opsboard/projects', {
      statusCode: 200,
      body: [
        {
          id: 'project-1',
          name: projectToDelete,
          api_key: 'test-key',
          org: { id: 'org-1', name: 'Test Organization' },
        },
      ],
    }).as('loadProjectsData');

    cy.intercept('POST', '**/opsboard/projects/project-1/delete', {
      statusCode: 200,
      body: { success: true },
    }).as('deleteProject');

    cy.visit('/settings/projects');
    cy.wait(['@loadOrgsData', '@loadProjectsData']);

    cy.wait(500);

    cy.get(
      `tr[data-testid="project-row"][data-project-name="${projectToDelete}"] > :last-child`,
    ).within(() => {
      cy.getDataTestId('delete-project-trigger').should('be.visible').click();
    });

    cy.getDataTestId('delete-project-confirm').should('be.visible').click();

    cy.wait('@deleteProject');

    cy.get('[data-testid^="toast-default-"]')
      .should('be.visible')
      .and('contain.text', 'Project Deleted');
  });

  it('should handle errors when no organizations exist', () => {
    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [],
    }).as('loadEmptyOrgs');

    cy.visit('/settings/projects');
    cy.wait('@loadEmptyOrgs');

    cy.getDataTestId('projects-settings-header').should('be.visible');

    cy.get('body').then(($body) => {
      const bodyText = $body.text();
      expect(bodyText).to.satisfy(
        (text: string) =>
          text.includes('No organizations found') || text.includes('Error loading organizations'),
      );
    });
  });

  it('should handle API errors gracefully', () => {
    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 500,
      body: { error: 'Internal server error' },
    }).as('loadOrgsError');

    cy.visit('/settings/projects');
    cy.wait('@loadOrgsError');

    cy.getDataTestId('projects-settings-header').should('be.visible');

    cy.log('API errors handled gracefully - page loads without crashing');
  });

  it('should handle project creation errors', () => {
    cy.intercept('GET', '**/opsboard/orgs', {
      statusCode: 200,
      body: [
        {
          id: 'org-1',
          name: 'Test Organization',
          prem_status: 'pro',
          current_user_role: 'owner',
        },
      ],
    }).as('loadOrgsData');

    cy.intercept('GET', '**/opsboard/projects', {
      statusCode: 200,
      body: [],
    }).as('loadProjectsData');

    cy.intercept('POST', '**/opsboard/projects', {
      statusCode: 500,
      body: { error: 'Failed to create project' },
    }).as('createProjectError');

    cy.visit('/settings/projects');
    cy.wait(['@loadOrgsData', '@loadProjectsData']);

    cy.getDataTestId('projects-settings-button-create-new-project-org-1').click();
    cy.getDataTestId('new-project-input').last().type('Failed Project');
    cy.getDataTestId('create-project-confirm').last().click();

    cy.wait('@createProjectError');

    cy.get('[data-testid^="toast-destructive-"]')
      .should('be.visible')
      .and('contain.text', 'Failed to Create Project');
  });
});
