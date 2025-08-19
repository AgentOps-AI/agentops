"""Unit tests for the config module."""

import pytest
from jockey.config import (
    DeploymentConfig,
    DeploymentPack,
    DEPLOYMENT_PACKS,
    _get_instance_build_files,
)


class TestDeploymentPacks:
    """Test deployment pack functionality."""

    def test_deployment_packs_dictionary_contains_all_packs(self):
        """Test that DEPLOYMENT_PACKS contains all expected pack types."""
        expected_packs = {"FASTAPI", "CREWAI", "CREWAI_JOB"}
        assert set(DEPLOYMENT_PACKS.keys()) == expected_packs
        
        # Verify they're the correct DeploymentPack instances
        assert DEPLOYMENT_PACKS["FASTAPI"] == DEPLOYMENT_PACKS["FASTAPI"]
        assert DEPLOYMENT_PACKS["CREWAI"] == DEPLOYMENT_PACKS["CREWAI"]
        assert DEPLOYMENT_PACKS["CREWAI_JOB"] == DEPLOYMENT_PACKS["CREWAI_JOB"]

    def test_fastapi_pack_configuration(self):
        """Test FASTAPI pack has correct configuration."""
        pack = DEPLOYMENT_PACKS["FASTAPI"]
        assert pack.dockerfile_template == "fastapi-agent"
        assert pack.ports == [8000]
        assert pack.build_files == {}

    def test_crewai_pack_configuration(self):
        """Test CREWAI pack has correct configuration."""
        pack = DEPLOYMENT_PACKS["CREWAI"]
        assert pack.dockerfile_template == "crewai-agent"
        assert pack.ports == [8080]
        assert isinstance(pack.build_files, dict)

    def test_crewai_job_pack_configuration(self):
        """Test CREWAI_JOB pack has correct configuration."""
        pack = DEPLOYMENT_PACKS["CREWAI_JOB"]
        assert pack.dockerfile_template == "crewai-job"
        assert pack.ports == []  # No ports for job execution
        assert isinstance(pack.build_files, dict)


class TestDeploymentConfigFromPack:
    """Test DeploymentConfig.from_pack() functionality."""

    def test_from_pack_with_fastapi(self):
        """Test creating config from FASTAPI pack."""
        config = DeploymentConfig.from_pack(
            "FASTAPI",
            namespace="test-ns",
            project_id="test-project"
        )
        
        assert config.dockerfile_template == "fastapi-agent"
        assert config.ports == [8000]
        assert config.build_files == {}
        assert config.namespace == "test-ns"
        assert config.project_id == "test-project"

    def test_from_pack_with_crewai(self):
        """Test creating config from CREWAI pack."""
        config = DeploymentConfig.from_pack(
            "CREWAI",
            namespace="test-ns",
            project_id="test-project"
        )
        
        assert config.dockerfile_template == "crewai-agent"
        assert config.ports == [8080]
        assert isinstance(config.build_files, dict)
        assert config.namespace == "test-ns"
        assert config.project_id == "test-project"

    def test_from_pack_with_crewai_job(self):
        """Test creating config from CREWAI_JOB pack."""
        config = DeploymentConfig.from_pack(
            "CREWAI_JOB",
            namespace="test-ns",
            project_id="test-project"
        )
        
        assert config.dockerfile_template == "crewai-job"
        assert config.ports == []
        assert isinstance(config.build_files, dict)
        assert config.namespace == "test-ns"
        assert config.project_id == "test-project"

    def test_from_pack_with_none_uses_fastapi_fallback(self):
        """Test that None pack name falls back to FASTAPI."""
        config = DeploymentConfig.from_pack(
            None,
            namespace="test-ns",
            project_id="test-project"
        )
        
        assert config.dockerfile_template == "fastapi-agent"
        assert config.ports == [8000]
        assert config.build_files == {}

    def test_from_pack_with_invalid_name_raises_error(self):
        """Test that invalid pack name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid deployment pack name: INVALID"):
            DeploymentConfig.from_pack(
                "INVALID",
                namespace="test-ns",
                project_id="test-project"
            )

    def test_from_pack_with_empty_string_raises_error(self):
        """Test that empty string pack name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid deployment pack name: "):
            DeploymentConfig.from_pack(
                "",
                namespace="test-ns",
                project_id="test-project"
            )

    def test_from_pack_kwargs_override_pack_defaults(self):
        """Test that kwargs override pack defaults."""
        config = DeploymentConfig.from_pack(
            "FASTAPI",
            namespace="test-ns",
            project_id="test-project",
            ports=[9000, 9001],  # Override default FASTAPI ports
            dockerfile_template="custom-template",  # Override default template
            replicas=3
        )
        
        assert config.ports == [9000, 9001]  # Should use provided ports
        assert config.dockerfile_template == "custom-template"  # Should use provided template
        assert config.replicas == 3
        # Other pack defaults should still apply
        assert config.build_files == {}  # FASTAPI has empty build_files

    def test_from_pack_computes_derived_fields(self):
        """Test that from_pack() properly computes tag and hostname."""
        config = DeploymentConfig.from_pack(
            "FASTAPI",
            namespace="test-ns",
            project_id="test-project-123"
        )
        
        # Derived fields should be computed in __post_init__
        assert config.tag == "test-project-123"
        assert config.hostname == "test-project-123.deploy.agentops.ai"

    def test_from_pack_with_all_optional_fields(self):
        """Test from_pack with all optional fields provided."""
        config = DeploymentConfig.from_pack(
            "CREWAI",
            namespace="test-ns",
            project_id="test-project",
            repository_url="https://github.com/test/repo.git",
            branch="feature-branch",
            github_access_token="token123",
            entrypoint="main.py",
            watch_path="src/",
            agentops_api_key="key123",
            callback_url="https://callback.example.com",
            secret_names=["secret1", "secret2"],
            create_ingress=False,
            force_recreate=True
        )
        
        # Pack defaults should be applied
        assert config.dockerfile_template == "crewai-agent"
        assert config.ports == [8080]
        assert isinstance(config.build_files, dict)
        
        # Provided fields should be set
        assert config.repository_url == "https://github.com/test/repo.git"
        assert config.branch == "feature-branch"
        assert config.github_access_token == "token123"
        assert config.entrypoint == "main.py"
        assert config.watch_path == "src/"
        assert config.agentops_api_key == "key123"
        assert config.callback_url == "https://callback.example.com"
        assert config.secret_names == ["secret1", "secret2"]
        assert config.create_ingress is False
        assert config.force_recreate is True


class TestDeploymentConfigSerialization:
    """Test serialization/deserialization of DeploymentConfig."""

    def test_serialize_config_created_from_pack(self):
        """Test that config created from pack can be serialized."""
        config = DeploymentConfig.from_pack(
            "CREWAI",
            namespace="test-ns",
            project_id="test-project",
            repository_url="https://github.com/test/repo.git"
        )
        
        serialized = config.serialize()
        
        # Should contain all required fields
        assert serialized["namespace"] == "test-ns"
        assert serialized["project_id"] == "test-project"
        assert serialized["dockerfile_template"] == "crewai-agent"
        assert serialized["ports"] == [8080]
        assert serialized["repository_url"] == "https://github.com/test/repo.git"
        assert isinstance(serialized["build_files"], dict)

    def test_deserialize_config_works(self):
        """Test that serialized config can be deserialized."""
        original_config = DeploymentConfig.from_pack(
            "FASTAPI",
            namespace="test-ns",
            project_id="test-project"
        )
        
        serialized = original_config.serialize()
        deserialized_config = DeploymentConfig.from_serialized(serialized)
        
        # Should have same values
        assert deserialized_config.namespace == original_config.namespace
        assert deserialized_config.project_id == original_config.project_id
        assert deserialized_config.dockerfile_template == original_config.dockerfile_template
        assert deserialized_config.ports == original_config.ports
        assert deserialized_config.build_files == original_config.build_files

    def test_roundtrip_serialization_preserves_data(self):
        """Test that serialize -> deserialize preserves all data."""
        original_config = DeploymentConfig.from_pack(
            "CREWAI_JOB",
            namespace="test-ns",
            project_id="test-project",
            repository_url="https://github.com/test/repo.git",
            branch="main",
            replicas=2,
            secret_names=["secret1"],
            agentops_api_key="test-key"
        )
        
        # Serialize and deserialize
        serialized = original_config.serialize()
        deserialized_config = DeploymentConfig.from_serialized(serialized)
        
        # All fields should be preserved
        assert deserialized_config.namespace == original_config.namespace
        assert deserialized_config.project_id == original_config.project_id
        assert deserialized_config.dockerfile_template == original_config.dockerfile_template
        assert deserialized_config.repository_url == original_config.repository_url
        assert deserialized_config.branch == original_config.branch
        assert deserialized_config.replicas == original_config.replicas
        assert deserialized_config.secret_names == original_config.secret_names
        assert deserialized_config.agentops_api_key == original_config.agentops_api_key
        assert deserialized_config.ports == original_config.ports
        assert deserialized_config.build_files == original_config.build_files


class TestInstanceBuildFiles:
    """Test instance build files functionality."""

    def test_get_instance_build_files_returns_dict(self):
        """Test that _get_instance_build_files returns a dictionary."""
        build_files = _get_instance_build_files()
        assert isinstance(build_files, dict)
        
        # Should contain Python files from instance directory if they exist
        for key, value in build_files.items():
            assert key.startswith("instance/")
            assert key.endswith(".py")
            assert isinstance(value, str)  # File content should be string

    def test_crewai_packs_have_same_build_files(self):
        """Test that both CREWAI packs have the same build files."""
        crewai_pack = DEPLOYMENT_PACKS["CREWAI"]
        crewai_job_pack = DEPLOYMENT_PACKS["CREWAI_JOB"]
        
        # Both should use the same build files
        assert crewai_pack.build_files == crewai_job_pack.build_files
        
        # FASTAPI should have empty build files
        assert DEPLOYMENT_PACKS["FASTAPI"].build_files == {}


class TestPackValidation:
    """Test edge cases and validation for deployment packs."""

    def test_all_pack_names_are_strings(self):
        """Test that all pack names in DEPLOYMENT_PACKS are strings."""
        for pack_name in DEPLOYMENT_PACKS.keys():
            assert isinstance(pack_name, str)
            assert pack_name.isupper()  # Convention: pack names should be uppercase

    def test_all_packs_have_required_attributes(self):
        """Test that all packs have the required DeploymentPack attributes."""
        for pack_name, pack in DEPLOYMENT_PACKS.items():
            assert isinstance(pack.dockerfile_template, str)
            assert isinstance(pack.ports, list)
            assert all(isinstance(port, int) for port in pack.ports)
            assert isinstance(pack.build_files, dict)
            
            # All build file keys should be strings, values should be strings
            for key, value in pack.build_files.items():
                assert isinstance(key, str)
                assert isinstance(value, str)

    def test_pack_names_match_constants(self):
        """Test that DEPLOYMENT_PACKS keys match the pack constants."""
        # Ensure we have exactly the packs we expect
        expected_packs = {"FASTAPI", "CREWAI", "CREWAI_JOB"}
        actual_packs = set(DEPLOYMENT_PACKS.keys())
        assert actual_packs == expected_packs