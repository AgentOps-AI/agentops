from typing import Iterable, Optional

from opentelemetry import metrics
from opentelemetry.metrics import CallbackOptions, Instrument, MeterProvider, Observation
from opentelemetry.sdk.metrics import MeterProvider as SDKMeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

from agentops.log_config import logger  # Import the configured AgentOps logger


class TelemetryMetrics:
    """
    Manages metrics collection for AgentOps telemetry
    """

    def __init__(self, service_name: str):
        self._meter_provider = self._setup_meter_provider()
        self._meter = self._meter_provider.get_meter(name=service_name, version="1.0.0")

        # Export counters
        self.export_attempts = self._meter.create_counter(
            name="agentops.export.attempts",
            description="Number of export attempts",
            unit="1",
        )

        self.export_failures = self._meter.create_counter(
            name="agentops.export.failures",
            description="Number of failed exports",
            unit="1",
        )

        # Export histograms
        self.export_duration = self._meter.create_histogram(
            name="agentops.export.duration",
            description="Duration of export operations",
            unit="ms",
        )

        self.batch_size = self._meter.create_histogram(
            name="agentops.export.batch_size",
            description="Size of export batches",
            unit="1",
        )

        # Memory usage gauge
        self._memory_gauge = self._meter.create_observable_gauge(
            name="agentops.memory.usage",
            description="Memory usage of the telemetry system",
            unit="bytes",
            callbacks=[self._get_memory_usage],
        )

    def _setup_meter_provider(self) -> MeterProvider:
        """Setup the meter provider with appropriate exporters"""
        # Create console exporter for development
        console_exporter = ConsoleMetricExporter()
        reader = PeriodicExportingMetricReader(console_exporter, export_interval_millis=5000)

        return SDKMeterProvider(
            metric_readers=[reader],
        )

    def _get_memory_usage(self, options: CallbackOptions) -> Iterable[Observation]:
        """Callback to get current memory usage"""
        try:
            import psutil

            process = psutil.Process()
            memory = process.memory_info().rss
            return [Observation(value=float(memory), attributes={"type": "process_memory"})]
        except Exception as e:
            logger.error(f"Failed to collect memory metrics: {e}")
            return []

    def record_export_attempt(self, success: bool, duration_ms: float, batch_size: int, error_type: str = None):
        """Record metrics for an export attempt"""
        # Record attempt
        self.export_attempts.add(1)

        # Record failure if applicable
        if not success:
            self.export_failures.add(1, {"error_type": error_type or "unknown"})

        # Record duration and batch size
        self.export_duration.record(duration_ms)
        self.batch_size.record(batch_size)

    def shutdown(self):
        """Shutdown metrics collection"""
        if isinstance(self._meter_provider, SDKMeterProvider):
            # Force a final export before shutdown
            for reader in self._meter_provider._all_metric_readers:
                reader.force_flush()
            # Then shutdown the provider
            self._meter_provider.shutdown()

# Add example usage
if __name__ == "__main__":
    import time
    import random
    
    # Initialize metrics with a test service name
    logger.info("Initializing TelemetryMetrics...")
    metrics = TelemetryMetrics("example-service")
    
    logger.info("Starting metrics collection example...")
    logger.info("Export interval: 5s, Running 5 iterations...")
    logger.info("-" * 80)
    
    # Example error types
    ERROR_TYPES = ["timeout", "connection_error", "invalid_data", "rate_limit", "server_error"]
    
    # Simulate some export operations
    for i in range(5):
        # Simulate successful export
        duration = 100.5 + i * 10
        batch_size = 5 + i
        
        logger.info(f"Iteration {i+1}:")
        logger.info(f"  ✓ Recording successful export (duration={duration}ms, batch_size={batch_size})")
        metrics.record_export_attempt(
            success=True,
            duration_ms=duration,
            batch_size=batch_size
        )
        
        # Simulate failed export with random error type
        error_type = random.choice(ERROR_TYPES)
        logger.info(f"  ✗ Recording failed export (duration=200.5ms, batch_size=3, error={error_type})")
        metrics.record_export_attempt(
            success=False,
            duration_ms=200.5,
            batch_size=3,
            error_type=error_type
        )
        
        # Log cumulative stats with error breakdown
        logger.info(f"  📊 Cumulative stats:")
        logger.info(f"     - Total attempts: {(i+1)*2}")
        logger.info(f"     - Failures: {i+1}")
        logger.info(f"     - Last batch size: {batch_size}")
        logger.info(f"     - Last error: {error_type}")
        logger.info("")
        
        # Wait to see metrics in console
        logger.info("Waiting for metrics export (5s)...")
        time.sleep(2)
    
    logger.info("-" * 80)
    logger.info("Metrics collection completed. Shutting down...")
    metrics.shutdown()
