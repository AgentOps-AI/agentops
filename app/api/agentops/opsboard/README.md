# Opsboard

The Opsboard module provides the backend API for user, organization, and project management in AgentOps. This module allows users to create and manage organizations, projects, and team members with role-based access controls.

## Architecture

Opsboard is a FastAPI application that serves REST API endpoints for the AgentOps dashboard. It uses:

- **FastAPI**: Web framework with automatic OpenAPI documentation
- **SQLAlchemy ORM**: Database access and object-relational mapping
- **Pydantic**: Data validation and serialization
- **Authentication**: Uses the AgentOps auth module for secure user authentication

The module is structured to provide a clean separation of concerns:

```
/opsboard
├── app.py                 # FastAPI application setup and middleware
├── environment.py         # Environment-specific configuration
├── models.py              # SQLAlchemy ORM models
├── routes.py              # Route configuration and endpoint definitions
├── schemas.py             # Pydantic models for request/response validation
└── views/                 # Business logic and handlers
    ├── users.py           # User management endpoints
    ├── orgs.py            # Organization management endpoints
    └── projects.py        # Project management endpoints
```

## Features

### User Management
- User profile management
- User preferences and settings
- Survey completion tracking

### Organization Management
- Create and manage organizations
- Invite users to organizations
- Role-based access control (owner, admin, developer, business_user)
- Organization membership management

### Project Management
- Create and manage projects within organizations
- Project environment configuration (production, staging, development, community)
- API key management for project access

## Models

The module uses the following primary data models:

- **UserModel**: User profile information
- **OrgModel**: Organization details
- **UserOrgModel**: User-organization relationships with roles
- **OrgInviteModel**: Pending invitations to organizations
- **ProjectModel**: Project configuration and API keys

## Authentication and Authorization

Opsboard uses the AgentOps auth module for authentication. All routes require authentication via the `AuthenticatedRoute` middleware. Authorization is managed through role-based permissions within the organization context.

## Endpoints

### User Endpoints
- `GET /opsboard/users/me`: Get authenticated user profile
- `POST /opsboard/users/update`: Update user profile
- `POST /opsboard/users/complete_survey`: Mark user survey as complete

### Organization Endpoints
- `GET /opsboard/orgs`: List organizations for the authenticated user
- `GET /opsboard/orgs/{org_id}`: Get organization details
- `POST /opsboard/orgs/create`: Create a new organization
- `POST /opsboard/orgs/{org_id}/update`: Update organization details
- `POST /opsboard/orgs/{org_id}/invite`: Invite a user to an organization
- `GET /opsboard/orgs/invites`: List pending organization invites
- `POST /opsboard/orgs/{org_id}/accept`: Accept an organization invitation
- `POST /opsboard/orgs/{org_id}/members/remove`: Remove a user from an organization
- `POST /opsboard/orgs/{org_id}/members/update`: Update a user's role in an organization
- `DELETE /opsboard/orgs/{org_id}`: Delete an organization

### Project Endpoints
- `GET /opsboard/projects`: List projects for the authenticated user
- `GET /opsboard/projects/{project_id}`: Get project details
- `POST /opsboard/projects`: Create a new project
- `POST /opsboard/projects/{project_id}/update`: Update project details
- `POST /opsboard/projects/{project_id}/delete`: Delete a project
- `POST /opsboard/projects/{project_id}/regenerate-key`: Regenerate project API key

## Premium Status

Organizations can have different premium statuses that affect available features:
- `free`: Basic features
- `pro`: Advanced features
- `enterprise`: Enterprise-level features and support

## Development

To run tests for the Opsboard module, use the project's test runner with the opsboard-specific tests:

```bash
# From the root of the project
pytest tests/opsboard/
```
