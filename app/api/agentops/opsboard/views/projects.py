import uuid
from fastapi import Request, Depends, HTTPException

from agentops.common.orm import get_orm_session, Session
from agentops.api.models.metrics import TraceCountsModel

from ..models import OrgModel, ProjectModel, Environment
from ..schemas import (
    StatusResponse,
    ProjectSummaryResponse,
    ProjectResponse,
    ProjectCreateSchema,
    ProjectUpdateSchema,
)


async def get_projects(
    *,
    request: Request,
    orm: Session = Depends(get_orm_session),
) -> list[ProjectSummaryResponse]:
    """
    Get all projects the user has access to across all organizations they belong to.
    Includes organization information with each project.

    Optimized version that reduces unnecessary data loading.
    """
    # Use a more efficient query that only loads what we need for the response
    projects = ProjectModel.get_all_for_user_optimized(orm, request.state.session.user_id)

    # Only fetch trace counts if we have projects
    if projects:
        _projects_counts = await TraceCountsModel.select(
            filters={'project_ids': [str(project.id) for project in projects]}
        )
        projects_counts: dict[str, int] = {str(p.project_id): p for p in _projects_counts}
    else:
        projects_counts = {}

    project_responses = []
    for project in projects:
        response = ProjectSummaryResponse.model_validate(project)

        # add trace metrics to the response
        if counts := projects_counts.get(str(project.id)):
            response.span_count = counts.span_count
            response.trace_count = counts.trace_count

        project_responses.append(response)

    return project_responses


def get_project(
    *,
    request: Request,
    project_id: str,
    orm: Session = Depends(get_orm_session),
) -> ProjectResponse:
    """
    Get a specific project by ID.
    User must be a member of the project's organization.
    """
    project = ProjectModel.get_by_id(orm, project_id)

    if not project or not project.org.is_user_member(request.state.session.user_id):
        raise HTTPException(status_code=404, detail="Project not found")

    project.org.set_current_user(request.state.session.user_id)
    return ProjectResponse.model_validate(project)


def create_project(
    *,
    request: Request,
    orm: Session = Depends(get_orm_session),
    body: ProjectCreateSchema,
) -> ProjectResponse:
    """
    Create a new project in an organization.
    User must be an admin or owner of the organization.
    """
    org = OrgModel.get_by_id(orm, body.org_id)

    if not org or not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(status_code=404, detail="Organization not found")

    if org.max_project_count and not org.current_project_count < org.max_project_count:
        raise HTTPException(status_code=403, detail="Organization has reached it's project limit")

    environment = Environment(body.environment) if body.environment else Environment.development
    project = ProjectModel(
        name=body.name,
        org_id=body.org_id,
        environment=environment,
    )

    orm.add(project)
    orm.commit()

    # explicitly load the project so we have all context needed for the response
    project = ProjectModel.get_by_id(orm, project.id)
    project.org.set_current_user(request.state.session.user_id)
    return ProjectResponse.model_validate(project)


def update_project(
    *,
    request: Request,
    project_id: str,
    orm: Session = Depends(get_orm_session),
    body: ProjectUpdateSchema,
) -> ProjectResponse:
    """
    Update a project's name or environment.
    User must be an admin or owner of the organization.
    """
    project = ProjectModel.get_by_id(orm, project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(status_code=403, detail="You don't have permission to update this project")

    if body.name is not None:
        project.name = body.name

    if body.environment is not None:
        try:
            project.environment = Environment(body.environment)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid environment")

    orm.commit()

    # reload project cuz it's more flexible than calling orm.refresh with args
    project = ProjectModel.get_by_id(orm, project.id)
    project.org.set_current_user(request.state.session.user_id)
    return ProjectResponse.model_validate(project)


def delete_project(
    *,
    request: Request,
    project_id: str,
    orm: Session = Depends(get_orm_session),
) -> StatusResponse:
    """
    Delete a project.
    User must be an owner of the organization.
    """
    project = ProjectModel.get_by_id(orm, project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.org.is_user_owner(request.state.session.user_id):
        raise HTTPException(status_code=403, detail="Only organization owners can delete projects")

    orm.delete(project)
    orm.commit()

    return StatusResponse(message="Project deleted successfully")


def regenerate_api_key(
    *,
    request: Request,
    project_id: str,
    orm: Session = Depends(get_orm_session),
) -> ProjectResponse:
    """
    Regenerate the API key for a project.
    User must be an admin or owner of the organization.
    """
    project = ProjectModel.get_by_id(orm, project_id)

    if not project or not project.org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(status_code=404, detail="Project not found")

    project.api_key = str(uuid.uuid4())
    orm.commit()

    # reload project cuz it's more flexible than calling orm.refresh with args
    project = ProjectModel.get_by_id(orm, project.id)
    project.org.set_current_user(request.state.session.user_id)
    return ProjectResponse.model_validate(project)
