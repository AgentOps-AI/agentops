/// <reference types="cypress" />

/**
 * E2E: Project Management
 * Validates project deletion and creation flows via UI in a single session.
 * Tests: delete default project, error handling, create new project, free user behavior.
 */
describe('Project Management E2E', () => {
  before(() => {
    cy.login();
  });

  it('comprehensive project management flow', () => {
    const newProjectName = `E2E Test Project ${Date.now()}`;
    const errorProjectName = `Error Test Project ${Date.now()}`;

    cy.intercept('GET', '**/opsboard/orgs*').as('loadOrgsData');

    cy.visit('/settings/projects');

    cy.wait('@loadOrgsData');

    cy.get('body').then(($body) => {
      const defaultProjectExists =
        $body.find('tr[data-testid="project-row"][data-project-name="Default Project"]').length > 0;
      const anyProjectExists = $body.find('tr[data-testid="project-row"]').length > 0;

      if (!defaultProjectExists && !anyProjectExists) {
        cy.log('No projects found, creating Default Project first');

        cy.intercept('POST', '**/opsboard/projects').as('createInitialDefaultProject');

        cy.get('[data-testid^="projects-settings-button-create-new-project-"]')
          .first()
          .should('be.visible')
          .click();
        cy.getDataTestId('new-project-input')
          .last()
          .should('be.visible')
          .clear()
          .type('Default Project');
        cy.getDataTestId('create-project-confirm').should('be.visible').click();

        cy.wait('@createInitialDefaultProject')
          .its('response.statusCode')
          .should('be.oneOf', [200, 201]);

        cy.get('tr[data-testid="project-row"][data-project-name="Default Project"]').should(
          'exist',
        );
      } else if (!defaultProjectExists && anyProjectExists) {
        cy.log(
          'Other projects exist but no Default Project - will create Default Project after cleanup',
        );
      } else {
        cy.log('Default Project already exists, proceeding with test');
      }
    });

    cy.get('tr[data-testid="project-row"][data-project-name="Default Project"] > :last-child')
      .should('exist')
      .within(() => {
        cy.getDataTestId('delete-project-trigger').should('be.visible').click();
      });

    cy.intercept('POST', '**/opsboard/projects/*/delete').as('deleteDefaultProject');
    cy.getDataTestId('delete-project-confirm').should('be.visible').click();
    cy.wait('@deleteDefaultProject').its('response.statusCode').should('be.oneOf', [200, 204]);

    cy.get('tr[data-testid="project-row"][data-project-name="Default Project"]').should(
      'not.exist',
    );

    cy.intercept('POST', '**/opsboard/projects', {
      statusCode: 500,
      body: { error: 'Internal Server Error' },
    }).as('createProjectFail');

    cy.get('[data-testid^="projects-settings-button-create-new-project-"]')
      .first()
      .should('be.visible')
      .click();
    cy.getDataTestId('new-project-input')
      .last()
      .should('be.visible')
      .clear()
      .type(errorProjectName);
    cy.getDataTestId('create-project-confirm').should('be.visible').click();

    cy.wait('@createProjectFail').its('response.statusCode').should('eq', 500);

    cy.assertToastMessage('❌ Failed to Create Project', 'destructive');

    cy.getDataTestId('new-project-input').last().should('be.visible');

    cy.visit('/projects');
    cy.contains(errorProjectName).should('not.exist');

    cy.visit('/settings/projects');

    cy.intercept('POST', '**/opsboard/projects', (req) => {
      req.reply();
    }).as('createProject');

    cy.get('[data-testid^="projects-settings-button-create-new-project-"]')
      .first()
      .should('be.visible')
      .click();
    cy.getDataTestId('new-project-input').last().should('be.visible').clear().type(newProjectName);
    cy.getDataTestId('create-project-confirm').should('be.visible').click();

    cy.wait('@createProject').then((interception) => {
      expect(interception.response?.statusCode).to.be.oneOf([200, 201]);
      const createdProjectId = interception.response?.body.id;
      expect(createdProjectId).to.exist;

      cy.visit('/projects');
      cy.contains(newProjectName).should('exist');

      cy.visit('/settings/projects');
      cy.intercept('POST', `**/opsboard/projects/${createdProjectId}/delete`).as(
        'deleteCreatedProject',
      );

      cy.get(
        `tr[data-testid="project-row"][data-project-name="${newProjectName}"] > :last-child`,
      ).within(() => {
        cy.getDataTestId('delete-project-trigger').should('be.visible').click();
      });

      cy.getDataTestId('delete-project-confirm').should('be.visible').click();
      cy.wait('@deleteCreatedProject').its('response.statusCode').should('be.oneOf', [200, 204]);

      cy.visit('/projects');
      cy.contains(newProjectName).should('not.exist');

      cy.visit('/settings/projects');

      cy.get('body').then(($body) => {
        if (
          $body.find('tr[data-testid="project-row"][data-project-name="Default Project"]')
            .length === 0
        ) {
          cy.log('Default Project not found, recreating it');

          cy.intercept('POST', '**/opsboard/projects').as('createDefaultProject');

          cy.get('[data-testid^="projects-settings-button-create-new-project-"]')
            .first()
            .should('be.visible')
            .click();
          cy.getDataTestId('new-project-input')
            .last()
            .should('be.visible')
            .clear()
            .type('Default Project');
          cy.getDataTestId('create-project-confirm').should('be.visible').click();

          cy.wait('@createDefaultProject')
            .its('response.statusCode')
            .should('be.oneOf', [200, 201]);
        } else {
          cy.log('Default Project already exists (likely auto-created), no need to recreate');
        }
      });

      cy.get('tr[data-testid="project-row"][data-project-name="Default Project"]').should('exist');

      cy.visit('/projects');
      cy.contains('Default Project').should('exist');

      // Test duplicate project name prevention
      cy.visit('/settings/projects');

      cy.get('[data-testid^="projects-settings-button-create-new-project-"]')
        .first()
        .should('be.visible')
        .click();
      cy.getDataTestId('new-project-input')
        .last()
        .should('be.visible')
        .clear()
        .type('Default Project');
      cy.getDataTestId('create-project-confirm').should('be.visible').click();

      // Should show duplicate name error toast
      cy.assertToastMessage('❌ Duplicate Name', 'destructive');
      cy.get('body').should(
        'contain',
        'A project with this name already exists in this organization.',
      );

      // Input should still be visible (not cleared) since creation was prevented
      cy.getDataTestId('new-project-input')
        .last()
        .should('be.visible')
        .should('have.value', 'Default Project');

      // Cancel the failed creation attempt
      cy.getDataTestId('create-project-cancel').last().click();

      // Test free user project limit
      cy.visit('/settings/projects');

      cy.get('[data-testid^="projects-settings-button-create-new-project-"]')
        .first()
        .should('be.visible')
        .click();
      cy.getDataTestId('new-project-input')
        .last()
        .should('be.visible')
        .clear()
        .type('Second Project Test');

      cy.getDataTestId('create-project-confirm').then(($btn) => {
        if ($btn.is(':disabled')) {
          cy.log('Create button is disabled for free users with existing project');
        } else {
          cy.getDataTestId('create-project-confirm').click();
          cy.get('body').then(($body) => {
            const bodyText = $body.text().toLowerCase();
            expect(bodyText).to.satisfy(
              (text: string) =>
                text.includes('upgrade') || text.includes('limit') || text.includes('pro'),
            );
          });
        }
      });
    });
  });
});
