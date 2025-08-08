import requests
from fastapi import Depends, HTTPException
from agentops.common.orm import get_orm_session, Session
from ...opsboard.models import ProjectModel
from ...opsboard.schemas import StatusResponse
from ..models import HostingProjectModel
from agentops.common.route_config import BaseView
from agentops.common.environment import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET


class GithubOAuthCallbackView(BaseView):
    """
    Exchange GitHub OAuth code for access token and store it in the deploy.projects table.
    """

    async def __call__(
        self,
        project_id: str,
        code: str,
        orm: Session = Depends(get_orm_session),
    ) -> StatusResponse:
        project = ProjectModel.get_by_id(orm, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="GitHub OAuth not configured in the API")

        # Exchange code for access token
        token_url = "https://github.com/login/oauth/access_token"
        headers = {"Accept": "application/json"}
        data = {
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
        }
        try:
            resp = requests.post(token_url, headers=headers, data=data)
            resp.raise_for_status()
            token_data = resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                error = token_data.get("error")
                raise HTTPException(status_code=400, detail="Failed to retrieve access token from GitHub. Error: " + error)

            # Create or update deploy.projects row
            deploy_project = orm.query(HostingProjectModel).filter_by(id=project.id).first()
            if not deploy_project:
                deploy_project = HostingProjectModel(
                    id=project.id,
                    github_oath_access_token=access_token,
                )
                orm.add(deploy_project)
            else:
                deploy_project.github_oath_access_token = access_token
            orm.commit()
            return StatusResponse(message="GitHub access token stored successfully in deploy.projects")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"GitHub OAuth failed: {str(e)}")


class GithubListReposView(BaseView):
    """
    Use the project's stored GitHub access token to list repos the user has access to.
    Handles pagination to fetch all repositories.
    """

    async def __call__(
        self,
        project_id: str,
        orm: Session = Depends(get_orm_session),
    ) -> list[dict]:
        project = HostingProjectModel.get_by_id(orm, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not project.github_oath_access_token:
            raise HTTPException(status_code=400, detail="No GitHub access token stored for this project")

        headers = {
            "Authorization": f"Bearer {project.github_oath_access_token}",
            "Accept": "application/vnd.github+json",
        }
        
        all_repos = []
        page = 1
        per_page = 100  # Maximum allowed by GitHub API
        
        try:
            while True:
                params = {
                    "page": page,
                    "per_page": per_page,
                    "sort": "created",  # Sort by creation date
                    "direction": "desc"  # Most recent first
                }
                
                resp = requests.get("https://api.github.com/user/repos", headers=headers, params=params)
                resp.raise_for_status()
                repos = resp.json()
                
                # If no repos returned, we've reached the end
                if not repos:
                    break
                
                # Add repos from this page
                all_repos.extend([
                    {
                        "id": repo["id"],
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "private": repo["private"],
                        "html_url": repo["html_url"],
                        "description": repo.get("description"),
                    }
                    for repo in repos
                ])
                
                # If we got fewer repos than per_page, we've reached the end
                if len(repos) < per_page:
                    break
                
                page += 1
                
            return all_repos
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch repos from GitHub: {str(e)}")