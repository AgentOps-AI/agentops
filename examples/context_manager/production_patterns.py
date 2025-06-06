"""
Production Patterns with Context Managers

This example demonstrates real-world production patterns using AgentOps
context managers, including monitoring, logging, and performance tracking.
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Any
import agentops
from agentops import agent, task, tool
from dotenv import load_dotenv

load_dotenv()

# Get API key from environment
AGENTOPS_API_KEY = os.environ.get("AGENTOPS_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@agent
class ProductionAgent:
    """A production-ready agent with monitoring."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.metrics = {"tasks_completed": 0, "errors_encountered": 0, "total_processing_time": 0.0}
        logger.info(f"Initialized production agent: {self.name}")

    @task
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a production request with monitoring."""
        start_time = time.time()

        try:
            logger.info(f"{self.name} processing request: {request_data.get('id', 'unknown')}")

            # Validate request
            validated_data = self.validate_request(request_data)

            # Process data
            processed_data = self.transform_data(validated_data)

            # Generate response
            response = self.generate_response(processed_data)

            # Update metrics
            processing_time = time.time() - start_time
            self.metrics["tasks_completed"] += 1
            self.metrics["total_processing_time"] += processing_time

            logger.info(f"{self.name} completed request in {processing_time:.3f}s")
            return response

        except Exception as e:
            self.metrics["errors_encountered"] += 1
            logger.error(f"{self.name} failed to process request: {e}")
            raise

    @tool
    def validate_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate incoming request data."""
        required_fields = ["id", "type", "payload"]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        logger.debug(f"{self.name} validated request: {data['id']}")
        return data

    @tool
    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform and enrich the data."""
        # Simulate data transformation
        time.sleep(0.01)  # Simulate processing time

        transformed = {
            **data,
            "processed_at": datetime.now().isoformat(),
            "processed_by": self.name,
            "version": self.config.get("version", "1.0"),
        }

        logger.debug(f"{self.name} transformed data for: {data['id']}")
        return transformed

    @tool
    def generate_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the final response."""
        response = {
            "status": "success",
            "request_id": data["id"],
            "result": f"Processed {data['type']} successfully",
            "metadata": {
                "processed_at": data["processed_at"],
                "processed_by": data["processed_by"],
                "version": data["version"],
            },
        }

        logger.debug(f"{self.name} generated response for: {data['id']}")
        return response

    def get_metrics(self) -> Dict[str, Any]:
        """Get current agent metrics."""
        avg_processing_time = self.metrics["total_processing_time"] / max(self.metrics["tasks_completed"], 1)

        return {
            **self.metrics,
            "average_processing_time": avg_processing_time,
            "error_rate": self.metrics["errors_encountered"]
            / max(self.metrics["tasks_completed"] + self.metrics["errors_encountered"], 1),
        }


def api_endpoint_pattern():
    """Example of using context managers in API endpoint pattern."""
    print("API Endpoint Pattern")

    agentops.init(api_key=AGENTOPS_API_KEY)

    # Simulate API requests
    requests = [
        {"id": "req_001", "type": "user_query", "payload": {"query": "What is AI?"}},
        {"id": "req_002", "type": "data_analysis", "payload": {"dataset": "sales_data"}},
        {"id": "req_003", "type": "user_query", "payload": {"query": "Process this"}},
    ]

    agent_config = {"version": "2.1.0", "environment": "production"}
    api_agent = ProductionAgent("APIAgent", agent_config)

    for request in requests:
        try:
            with agentops.start_trace("api_request", tags=["api", request["type"]]):
                response = api_agent.process_request(request)
                logger.info(f"API Response: {response['status']} for {response['request_id']}")

        except Exception as e:
            logger.error(f"API request failed: {e}")

    # Print final metrics
    print(f"Agent Metrics: {api_agent.get_metrics()}")


def batch_processing_pattern():
    """Example of batch processing with context managers."""
    print("\nBatch Processing Pattern")

    agentops.init(api_key=AGENTOPS_API_KEY)

    # Simulate batch data
    batch_data = [{"id": f"item_{i:03d}", "type": "data_record", "payload": {"value": i * 10}} for i in range(1, 6)]

    agent_config = {"version": "1.5.0", "batch_size": 5}
    batch_agent = ProductionAgent("BatchAgent", agent_config)

    with agentops.start_trace("batch_processing", tags=["batch", "bulk"]):
        logger.info(f"Starting batch processing of {len(batch_data)} items")

        successful_items = 0
        failed_items = 0

        for item in batch_data:
            try:
                with agentops.start_trace("item_processing", tags=["batch", "item"]):
                    batch_agent.process_request(item)
                    successful_items += 1
                    logger.debug(f"Processed item: {item['id']}")

            except Exception as e:
                failed_items += 1
                logger.error(f"Failed to process item {item['id']}: {e}")

        logger.info(f"Batch completed: {successful_items} successful, {failed_items} failed")

    print(f"Batch Agent Metrics: {batch_agent.get_metrics()}")


def microservice_pattern():
    """Example of microservice communication pattern."""
    print("\nMicroservice Communication Pattern")

    agentops.init(api_key=AGENTOPS_API_KEY)

    def authenticate_user(user_id: str) -> bool:
        """Simulate authentication service."""
        with agentops.start_trace("authenticate", tags=["auth", "security"]):
            logger.info(f"Authenticating user: {user_id}")
            time.sleep(0.01)  # Simulate auth check
            return user_id != "invalid_user"

    def get_user_profile(user_id: str) -> Dict[str, Any]:
        """Simulate user service."""
        with agentops.start_trace("get_profile", tags=["user", "profile"]):
            logger.info(f"Fetching profile for user: {user_id}")
            time.sleep(0.02)  # Simulate database query
            return {"user_id": user_id, "name": f"User {user_id}", "email": f"{user_id}@example.com"}

    def send_notification(user_id: str, message: str) -> bool:
        """Simulate notification service."""
        with agentops.start_trace("send_notification", tags=["notification", "email"]):
            logger.info(f"Sending notification to user: {user_id}")
            time.sleep(0.01)  # Simulate email sending
            return True

    # Simulate a complete user workflow
    user_requests = ["user_123", "user_456", "invalid_user"]

    for user_id in user_requests:
        try:
            with agentops.start_trace("user_workflow", tags=["workflow", "user"]):
                logger.info(f"Processing workflow for user: {user_id}")

                # Step 1: Authenticate
                if not authenticate_user(user_id):
                    raise ValueError(f"Authentication failed for user: {user_id}")

                # Step 2: Get profile
                get_user_profile(user_id)

                # Step 3: Send welcome notification
                send_notification(user_id, "Welcome to our service!")

                logger.info(f"Workflow completed for user: {user_id}")

        except Exception as e:
            logger.error(f"Workflow failed for user {user_id}: {e}")


def monitoring_pattern():
    """Example of monitoring with context managers."""
    print("\nMonitoring Pattern")

    agentops.init(api_key=AGENTOPS_API_KEY)

    class AlertManager:
        """Simple alert manager for demonstration."""

        def __init__(self):
            self.alerts = []

        def check_and_alert(self, trace_name: str, duration: float, success: bool):
            """Check conditions and generate alerts."""
            # Alert on slow operations
            if duration > 0.1:  # 100ms threshold
                self.alerts.append(
                    {
                        "type": "SLOW_OPERATION",
                        "trace": trace_name,
                        "duration": duration,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                logger.warning(f"SLOW OPERATION ALERT: {trace_name} took {duration:.3f}s")

            # Alert on failures
            if not success:
                self.alerts.append(
                    {"type": "OPERATION_FAILURE", "trace": trace_name, "timestamp": datetime.now().isoformat()}
                )
                logger.warning(f"FAILURE ALERT: {trace_name} failed")

    alert_manager = AlertManager()

    class MonitoredOperation:
        """Context manager with built-in monitoring and alerting."""

        def __init__(self, operation_name: str, tags: list = None):
            self.operation_name = operation_name
            self.tags = tags or []
            self.start_time = None
            self.trace_context = None

        def __enter__(self):
            self.start_time = time.time()
            self.trace_context = agentops.start_trace(self.operation_name, tags=self.tags)
            return self.trace_context

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            success = exc_type is None

            # Check for alerts
            alert_manager.check_and_alert(self.operation_name, duration, success)

            return False

    # Simulate operations with different performance characteristics
    operations = [
        ("fast_operation", 0.01, False),  # Fast, successful
        ("slow_operation", 0.15, False),  # Slow, successful (will trigger alert)
        ("failing_operation", 0.05, True),  # Fast, but fails (will trigger alert)
        ("normal_operation", 0.03, False),  # Normal, successful
    ]

    for op_name, sleep_time, should_fail in operations:
        try:
            with MonitoredOperation(op_name, tags=["monitoring", "demo"]):
                logger.info(f"Executing {op_name}")
                time.sleep(sleep_time)

                if should_fail:
                    raise RuntimeError(f"Simulated failure in {op_name}")

                logger.info(f"{op_name} completed successfully")

        except Exception as e:
            logger.error(f"{op_name} failed: {e}")

    # Print alerts
    print(f"Generated {len(alert_manager.alerts)} alerts:")
    for alert in alert_manager.alerts:
        print(f"   {alert['type']}: {alert.get('trace', 'unknown')} at {alert['timestamp']}")


if __name__ == "__main__":
    print("AgentOps Production Patterns Examples")
    print("=" * 50)

    # API endpoint pattern
    api_endpoint_pattern()

    # Batch processing pattern
    batch_processing_pattern()

    # Microservice pattern
    microservice_pattern()

    # Monitoring pattern
    monitoring_pattern()

    print("\nAll production pattern examples completed!")
