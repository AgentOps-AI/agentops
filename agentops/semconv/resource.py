"""
Resource attribute semantic conventions for AgentOps.

This module defines standard resource attributes used to identify resources in
AgentOps telemetry data.
"""


class ResourceAttributes:
    """
    Resource attributes for AgentOps.

    These attributes provide standard identifiers for resources being monitored
    or interacted with by AgentOps.
    """

    # Project identifier - uniquely identifies an AgentOps project
    PROJECT_ID = "agentops.project.id"

    # Service attributes
    SERVICE_NAME = "service.name"
    SERVICE_VERSION = "service.version"

    # Environment attributes
    ENVIRONMENT = "agentops.environment"
    DEPLOYMENT_ENVIRONMENT = "deployment.environment"

    # SDK attributes
    SDK_NAME = "agentops.sdk.name"
    SDK_VERSION = "agentops.sdk.version"
