"""Integration tests for deployment API endpoints using direct view calls."""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from agentops.deploy.models import HostingProjectModel
from agentops.opsboard.models import ProjectModel
from agentops.deploy.views.deploy import (
    CreateUpdateSecretView,
    ListSecretsView,
    InitiateDeploymentView,
    DeploymentStatusView,
    DeploymentHistoryView,
)
from agentops.deploy.schemas import CreateSecretRequest


@pytest.fixture
def mock_hosting_project():
    """Mock hosting project model."""
    hosting_project = Mock(spec=HostingProjectModel)
    hosting_project.id = "project-123"
    hosting_project.namespace = "test-namespace"
    hosting_project.app_name = "test-app"
    hosting_project.git_url = "https://github.com/test/repo"
    hosting_project.git_branch = "main"
    hosting_project.entrypoint = "main.py"
    hosting_project.github_oath_access_token = "token123"
    hosting_project.pack_name = "FASTAPI"  # Default pack for tests
    return hosting_project


@pytest.fixture
def mock_project():
    """Mock project model."""
    project = Mock(spec=ProjectModel)
    project.id = "project-123"
    project.name = "Test Project"
    project.org = Mock()
    project.org.is_user_member.return_value = True
    return project


@pytest.fixture(scope="session")
def mock_request():
    """Create a mock request with a session user_id."""
    from unittest.mock import MagicMock
    from fastapi import Request

    request = MagicMock(spec=Request)
    request.state.session.user_id = "00000000-0000-0000-0000-000000000001"
    return request


class TestDeploymentSecretsAPI:
    """Test the deployment secrets API endpoints."""

    @patch('agentops.deploy.views.deploy.delete_secret')
    @patch('agentops.deploy.views.deploy.create_secret')
    async def test_create_secret_success(
        self,
        mock_create,
        mock_delete,
        mock_request,
        orm_session,
        mock_hosting_project,
        mock_project,
    ):
        """Test creating a secret via view function."""
        # Setup mocks
        mock_delete.return_value = True
        mock_create.return_value = Mock()

        with (
            patch.object(HostingProjectModel, 'get_by_id', return_value=mock_hosting_project),
            patch.object(ProjectModel, 'get_by_id', return_value=mock_project),
        ):
            # Create the view and call it directly
            view = CreateUpdateSecretView(mock_request)
            body = CreateSecretRequest(name="DATABASE_URL", value="postgresql://localhost:5432/test")
            
            response = await view(
                project_id="project-123",
                body=body,
                orm=orm_session,
            )

            assert response.success is True
            assert response.message == "Successfully created secret"

    @patch('agentops.deploy.views.deploy.list_secrets')
    async def test_list_secrets_success(
        self, mock_list_secrets, mock_request, orm_session, mock_hosting_project, mock_project
    ):
        """Test listing secrets via view function."""
        # Setup mocks
        mock_list_secrets.return_value = ["DATABASE_URL", "API_KEY"]

        with (
            patch.object(HostingProjectModel, 'get_by_id', return_value=mock_hosting_project),
            patch.object(ProjectModel, 'get_by_id', return_value=mock_project),
        ):
            # Create the view and call it directly
            view = ListSecretsView(mock_request)
            
            response = await view(
                project_id="project-123",
                orm=orm_session,
            )

            assert len(response.secrets) == 2
            secret_names = [secret.name for secret in response.secrets]
            assert "DATABASE_URL" in secret_names
            assert "API_KEY" in secret_names

    async def test_deployment_not_found(self, mock_request, orm_session):
        """Test view response when deployment doesn't exist."""
        with patch.object(ProjectModel, 'get_by_id', return_value=None):
            # Create the view and call it directly
            view = ListSecretsView(mock_request)
            
            with pytest.raises(HTTPException) as exc_info:
                await view(
                    project_id="00000000-0000-0000-0000-000000000000",
                    orm=orm_session,
                )
            
            assert exc_info.value.status_code == 404
            assert "Project not found" in str(exc_info.value.detail)


class TestDeploymentManagementAPI:
    """Test the deployment management API endpoints."""

    @patch('agentops.deploy.views.deploy.queue_task')
    @patch('agentops.deploy.views.deploy.list_secrets')
    async def test_initiate_deployment_success(
        self,
        mock_list_secrets,
        mock_queue,
        mock_request,
        orm_session,
        mock_hosting_project,
        mock_project,
    ):
        """Test initiating a deployment via view function."""
        # Setup mocks
        mock_list_secrets.return_value = ["DATABASE_URL"]
        mock_queue.return_value = "job-456"

        with (
            patch.object(HostingProjectModel, 'get_by_id', return_value=mock_hosting_project),
            patch.object(ProjectModel, 'get_by_id', return_value=mock_project),
        ):
            # Create the view and call it directly
            view = InitiateDeploymentView(mock_request)
            
            response = await view(
                project_id="project-123",
                orm=orm_session,
            )

            assert response.success is True
            assert response.message == "Deployment initiated successfully"
            assert response.job_id == "job-456"

    @patch('agentops.deploy.views.deploy.get_task_events')
    async def test_deployment_status_success(
        self, mock_get_events, mock_request, orm_session, mock_hosting_project, mock_project
    ):
        """Test getting deployment status via view function."""
        from datetime import datetime
        from enum import Enum
        
        class MockStatus(Enum):
            SUCCESS = "success"
        
        # Setup mocks
        mock_events = [
            Mock(
                event_type="build",
                status=MockStatus.SUCCESS,
                message="Build completed",
                timestamp=datetime.fromisoformat("2024-01-01T00:00:00"),
            ),
        ]
        mock_get_events.return_value = mock_events

        with (
            patch.object(HostingProjectModel, 'get_by_id', return_value=mock_hosting_project),
            patch.object(ProjectModel, 'get_by_id', return_value=mock_project),
        ):
            # Create the view and call it directly
            view = DeploymentStatusView(mock_request)
            
            response = await view(
                project_id="project-123",
                job_id="test-job-123",
                orm=orm_session,
            )

            assert len(response.events) == 1
            assert response.events[0].type == "build"
            assert response.events[0].status == "success"
            assert response.events[0].message == "Build completed"

    @patch('agentops.deploy.views.deploy.get_task_events')
    async def test_deployment_status_with_start_date(
        self, mock_get_events, mock_request, orm_session, mock_hosting_project, mock_project
    ):
        """Test getting deployment status with start date filter via view function."""
        from datetime import datetime
        
        # Setup mocks
        mock_get_events.return_value = []

        with (
            patch.object(HostingProjectModel, 'get_by_id', return_value=mock_hosting_project),
            patch.object(ProjectModel, 'get_by_id', return_value=mock_project),
        ):
            # Create the view and call it directly
            view = DeploymentStatusView(mock_request)
            start_date = datetime.fromisoformat("2024-01-01T12:00:00")
            
            response = await view(
                project_id="project-123",
                job_id="test-job-456",
                start_date=start_date,
                orm=orm_session,
            )

            assert len(response.events) == 0


class TestViewValidation:
    """Test view validation and error handling."""

    @patch('agentops.deploy.views.deploy.create_secret')
    @patch('agentops.deploy.views.deploy.delete_secret')
    async def test_create_secret_kubernetes_error(
        self,
        mock_delete,
        mock_create,
        mock_request,
        orm_session,
        mock_hosting_project,
        mock_project,
    ):
        """Test creating a secret when Kubernetes operations fail."""
        # Setup mocks
        mock_delete.return_value = True
        mock_create.side_effect = Exception("Kubernetes API error")

        with (
            patch.object(HostingProjectModel, 'get_by_id', return_value=mock_hosting_project),
            patch.object(ProjectModel, 'get_by_id', return_value=mock_project),
        ):
            # Create the view and call it directly
            view = CreateUpdateSecretView(mock_request)
            body = CreateSecretRequest(name="DATABASE_URL", value="postgresql://localhost:5432/test")
            
            # The view should let the exception bubble up
            with pytest.raises(Exception) as exc_info:
                await view(
                    project_id="project-123",
                    body=body,
                    orm=orm_session,
                )
            
            assert "Kubernetes API error" in str(exc_info.value)


class TestDeploymentHistoryAPI:
    """Test the deployment history API endpoint."""

    @patch('agentops.deploy.views.deploy.get_task_status')
    @patch('agentops.deploy.views.deploy.get_tasks')
    async def test_deployment_history_success(
        self,
        mock_get_tasks,
        mock_get_status,
        mock_request,
        orm_session,
        mock_hosting_project,
        mock_project,
    ):
        """Test getting deployment history via view function."""
        from enum import Enum
        
        class MockStatus(Enum):
            SUCCESS = "success"
            RUNNING = "running"
        
        # Setup mock jobs
        mock_jobs = [
            {
                "job_id": "job-123",
                "project_id": "project-123",
                "namespace": "test-namespace",
                "queued_at": "2024-01-01T10:00:00",
                "config": {},
            },
            {
                "job_id": "job-456",
                "project_id": "project-123", 
                "namespace": "test-namespace",
                "queued_at": "2024-01-01T11:00:00",
                "config": {},
            },
        ]
        mock_get_tasks.return_value = mock_jobs
        
        # Setup mock status for each job (get_task_status returns BaseEvent)
        def mock_status_side_effect(job_id):
            if job_id == "job-123":
                return Mock(
                    status=MockStatus.SUCCESS,
                    message="Deployment completed successfully",
                )
            elif job_id == "job-456":
                return Mock(
                    status=MockStatus.RUNNING,
                    message="Deployment in progress",
                )
            return None
        
        mock_get_status.side_effect = mock_status_side_effect

        with (
            patch.object(HostingProjectModel, 'get_by_id', return_value=mock_hosting_project),
            patch.object(ProjectModel, 'get_by_id', return_value=mock_project),
        ):
            # Create the view and call it directly
            view = DeploymentHistoryView(mock_request)
            
            response = await view(
                project_id="project-123",
                orm=orm_session,
            )

            # Verify response
            assert len(response.jobs) == 2
            
            # Check first job
            job1 = response.jobs[0]
            assert job1.id == "job-123"
            assert job1.queued_at == "2024-01-01T10:00:00"
            assert job1.status == "success"
            assert job1.message == "Deployment completed successfully"
            
            # Check second job
            job2 = response.jobs[1]
            assert job2.id == "job-456"
            assert job2.queued_at == "2024-01-01T11:00:00"
            assert job2.status == "running"
            assert job2.message == "Deployment in progress"

    @patch('agentops.deploy.views.deploy.get_task_status')
    @patch('agentops.deploy.views.deploy.get_tasks')
    async def test_deployment_history_no_events(
        self,
        mock_get_tasks,
        mock_get_status,
        mock_request,
        orm_session,
        mock_hosting_project,
        mock_project,
    ):
        """Test deployment history when jobs have no events."""
        # Setup mock jobs
        mock_jobs = [
            {
                "job_id": "job-789",
                "project_id": "project-123",
                "namespace": "test-namespace", 
                "queued_at": "2024-01-01T12:00:00",
                "config": {},
            },
        ]
        mock_get_tasks.return_value = mock_jobs
        mock_get_status.return_value = None  # No events

        with (
            patch.object(HostingProjectModel, 'get_by_id', return_value=mock_hosting_project),
            patch.object(ProjectModel, 'get_by_id', return_value=mock_project),
        ):
            # Create the view and call it directly
            view = DeploymentHistoryView(mock_request)
            
            response = await view(
                project_id="project-123",
                orm=orm_session,
            )

            # Verify response
            assert len(response.jobs) == 1
            job = response.jobs[0]
            assert job.id == "job-789"
            assert job.queued_at == "2024-01-01T12:00:00"
            assert job.status == "unknown"
            assert job.message == ""

    @patch('agentops.deploy.views.deploy.get_tasks')
    async def test_deployment_history_empty_jobs(
        self,
        mock_get_tasks,
        mock_request,
        orm_session,
        mock_hosting_project,
        mock_project,
    ):
        """Test deployment history when no jobs exist."""
        mock_get_tasks.return_value = []  # No jobs

        with (
            patch.object(HostingProjectModel, 'get_by_id', return_value=mock_hosting_project),
            patch.object(ProjectModel, 'get_by_id', return_value=mock_project),
        ):
            # Create the view and call it directly
            view = DeploymentHistoryView(mock_request)
            
            response = await view(
                project_id="project-123",
                orm=orm_session,
            )

            # Verify response
            assert len(response.jobs) == 0


class TestDeploymentPacksAPI:
    """Test deployment pack functionality in API endpoints."""

    @pytest.fixture
    def mock_project_with_api_key(self):
        """Mock project model with API key."""
        project = Mock(spec=ProjectModel)
        project.id = "project-123"
        project.name = "Test Project"
        project.api_key = "test-api-key-123"
        project.org = Mock()
        project.org.is_user_member.return_value = True
        return project

    def test_hosting_project_deployment_config_with_fastapi_pack(self, mock_project_with_api_key):
        """Test that FASTAPI pack creates correct deployment config."""
        from jockey import DeploymentConfig
        from agentops.deploy.models import HostingProjectModel
        
        # Create hosting project with FASTAPI pack
        hosting_project = HostingProjectModel()
        hosting_project.id = "project-123"
        hosting_project.pack_name = "FASTAPI"
        hosting_project.git_url = "https://github.com/test/repo"
        hosting_project.git_branch = "main"
        hosting_project.entrypoint = "main.py"
        hosting_project.github_oath_access_token = "token123"
        hosting_project.watch_path = None
        hosting_project.user_callback_url = None
        hosting_project.project = mock_project_with_api_key
        
        # Mock list_secrets to return empty list
        with patch('jockey.list_secrets', return_value=[]):
            config = hosting_project.deployment_config
            
            # Verify FASTAPI pack defaults are applied
            assert config.dockerfile_template == "fastapi-agent"
            assert config.ports == [8000]
            assert config.build_files == {}
            assert config.namespace == "project-123"  # namespace property returns str(id)
            assert config.project_id == "project-123"

    def test_hosting_project_deployment_config_with_crewai_pack(self, mock_project_with_api_key):
        """Test that CREWAI pack creates correct deployment config."""
        from jockey import DeploymentConfig
        from agentops.deploy.models import HostingProjectModel
        
        # Create hosting project with CREWAI pack
        hosting_project = HostingProjectModel()
        hosting_project.id = "project-123"
        hosting_project.pack_name = "CREWAI"
        hosting_project.git_url = "https://github.com/test/repo"
        hosting_project.git_branch = "main"
        hosting_project.entrypoint = "main.py"
        hosting_project.github_oath_access_token = "token123"
        hosting_project.watch_path = "src/"
        hosting_project.user_callback_url = None
        hosting_project.project = mock_project_with_api_key
        
        # Mock list_secrets to return empty list
        with patch('jockey.list_secrets', return_value=[]):
            config = hosting_project.deployment_config
            
            # Verify CREWAI pack defaults are applied
            assert config.dockerfile_template == "crewai-agent"
            assert config.ports == [8080]
            assert isinstance(config.build_files, dict)  # Should have build files
            assert config.namespace == "project-123"  # namespace property returns str(id)
            assert config.project_id == "project-123"
            assert config.watch_path == "src/"

    def test_hosting_project_deployment_config_with_crewai_job_pack(self, mock_project_with_api_key):
        """Test that CREWAI_JOB pack creates correct deployment config."""
        from jockey import DeploymentConfig
        from agentops.deploy.models import HostingProjectModel
        
        # Create hosting project with CREWAI_JOB pack
        hosting_project = HostingProjectModel()
        hosting_project.id = "project-123"
        hosting_project.pack_name = "CREWAI_JOB"
        hosting_project.git_url = "https://github.com/test/repo"
        hosting_project.git_branch = "main"
        hosting_project.entrypoint = "main.py"
        hosting_project.github_oath_access_token = "token123"
        hosting_project.watch_path = "src/"
        hosting_project.user_callback_url = None
        hosting_project.project = mock_project_with_api_key
        
        # Mock list_secrets to return empty list
        with patch('jockey.list_secrets', return_value=[]):
            config = hosting_project.deployment_config
            
            # Verify CREWAI_JOB pack defaults are applied
            assert config.dockerfile_template == "crewai-job"
            assert config.ports == []  # No ports for job execution
            assert isinstance(config.build_files, dict)  # Should have build files
            assert config.namespace == "project-123"  # namespace property returns str(id)
            assert config.project_id == "project-123"

    def test_hosting_project_deployment_config_with_none_pack_fallback(self, mock_project_with_api_key):
        """Test that None pack_name falls back to FASTAPI."""
        from jockey import DeploymentConfig
        from agentops.deploy.models import HostingProjectModel
        
        # Create hosting project with None pack_name
        hosting_project = HostingProjectModel()
        hosting_project.id = "project-123"
        hosting_project.pack_name = None
        hosting_project.git_url = "https://github.com/test/repo"
        hosting_project.git_branch = "main"
        hosting_project.entrypoint = "main.py"
        hosting_project.github_oath_access_token = "token123"
        hosting_project.watch_path = None
        hosting_project.user_callback_url = None
        hosting_project.project = mock_project_with_api_key
        
        # Mock list_secrets to return empty list
        with patch('jockey.list_secrets', return_value=[]):
            config = hosting_project.deployment_config
            
            # Should fall back to FASTAPI defaults
            assert config.dockerfile_template == "fastapi-agent"
            assert config.ports == [8000]
            assert config.build_files == {}

    def test_hosting_project_deployment_config_with_invalid_pack_raises_error(self, mock_project_with_api_key):
        """Test that invalid pack_name raises ValueError."""
        from jockey import DeploymentConfig
        from agentops.deploy.models import HostingProjectModel
        
        # Create hosting project with invalid pack_name
        hosting_project = HostingProjectModel()
        hosting_project.id = "project-123"
        hosting_project.pack_name = "INVALID_PACK"
        hosting_project.git_url = "https://github.com/test/repo"
        hosting_project.git_branch = "main"
        hosting_project.entrypoint = "main.py"
        hosting_project.github_oath_access_token = "token123"
        hosting_project.watch_path = None
        hosting_project.user_callback_url = None
        hosting_project.project = mock_project_with_api_key
        
        # Mock list_secrets to return empty list
        with patch('jockey.list_secrets', return_value=[]):
            with pytest.raises(ValueError, match="Invalid deployment pack name: INVALID_PACK"):
                config = hosting_project.deployment_config

    @patch('agentops.deploy.views.deploy.queue_task')
    async def test_initiate_deployment_with_crewai_pack(
        self,
        mock_queue,
        mock_request,
        orm_session,
        mock_project_with_api_key,
    ):
        """Test that deployment uses correct pack configuration."""
        # Setup hosting project with CREWAI pack
        hosting_project = HostingProjectModel()
        hosting_project.id = "project-123"
        hosting_project.pack_name = "CREWAI"
        hosting_project.git_url = "https://github.com/test/repo"
        hosting_project.git_branch = "main"
        hosting_project.entrypoint = "main.py"
        hosting_project.github_oath_access_token = "token123"
        hosting_project.watch_path = "src/"
        hosting_project.user_callback_url = None
        hosting_project.project = mock_project_with_api_key
        
        # Setup mocks
        mock_queue.return_value = "job-456"
        
        with (
            patch.object(HostingProjectModel, 'get_by_id', return_value=hosting_project),
            patch.object(ProjectModel, 'get_by_id', return_value=mock_project_with_api_key),
            patch('jockey.list_secrets', return_value=["DATABASE_URL"]),
        ):
            # Create the view and call it directly
            view = InitiateDeploymentView(mock_request)
            
            response = await view(
                project_id="project-123",
                orm=orm_session,
            )

            # Verify response
            assert response.success is True
            assert response.message == "Deployment initiated successfully"
            assert response.job_id == "job-456"
            
            # Verify queue_task was called with correct config
            mock_queue.assert_called_once()
            call_args = mock_queue.call_args
            config = call_args[1]["config"]  # Get config from kwargs
            
            # Should have CREWAI pack defaults
            assert config.dockerfile_template == "crewai-agent"
            assert config.ports == [8080]
            assert isinstance(config.build_files, dict)
            assert len(config.build_files) > 0  # CREWAI should have build files

    @patch('agentops.deploy.views.deploy.queue_task')
    async def test_initiate_deployment_preserves_user_overrides(
        self,
        mock_queue,
        mock_request,
        orm_session,
        mock_project_with_api_key,
    ):
        """Test that user-provided fields override pack defaults."""
        # Setup hosting project with custom settings
        hosting_project = HostingProjectModel()
        hosting_project.id = "project-123"
        hosting_project.pack_name = "FASTAPI"
        hosting_project.git_url = "https://github.com/test/custom-repo"
        hosting_project.git_branch = "feature-branch"
        hosting_project.entrypoint = "custom_main.py"
        hosting_project.github_oath_access_token = "custom-token"
        hosting_project.watch_path = "custom/path/"
        hosting_project.user_callback_url = "https://custom-callback.com"
        hosting_project.project = mock_project_with_api_key
        
        # Setup mocks
        mock_queue.return_value = "job-789"
        
        with (
            patch.object(HostingProjectModel, 'get_by_id', return_value=hosting_project),
            patch.object(ProjectModel, 'get_by_id', return_value=mock_project_with_api_key),
            patch('jockey.list_secrets', return_value=["API_KEY"]),
        ):
            # Create the view and call it directly
            view = InitiateDeploymentView(mock_request)
            
            response = await view(
                project_id="project-123",
                orm=orm_session,
            )

            # Verify response
            assert response.success is True
            
            # Verify config has pack defaults but user overrides
            mock_queue.assert_called_once()
            call_args = mock_queue.call_args
            config = call_args[1]["config"]  # Get config from kwargs
            
            # Pack defaults
            assert config.dockerfile_template == "fastapi-agent"
            assert config.ports == [8000]
            assert config.build_files == {}
            
            # User overrides
            assert config.repository_url == "https://github.com/test/custom-repo"
            assert config.branch == "feature-branch"
            assert config.entrypoint == "custom_main.py"
            assert config.github_access_token == "custom-token"
            assert config.watch_path == "custom/path/"
            assert config.callback_url == "https://custom-callback.com"
            assert config.secret_names == ["API_KEY"]
            assert config.agentops_api_key == "test-api-key-123"
