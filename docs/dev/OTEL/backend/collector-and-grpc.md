Why gRPC for Logs?
	1.	Performance:
	•	gRPC uses HTTP/2, providing low-latency, high-throughput communication.
	•	Efficient for streaming large amounts of log data in real time.
	2.	Compression:
	•	gRPC supports built-in compression (e.g., gzip), reducing the overhead of transferring large log files.
	3.	Interoperability:
	•	Many OpenTelemetry-compatible backends (e.g., Jaeger, Prometheus, Datadog) expect data in gRPC OTLP format.
	4.	Standardization:
	•	gRPC is the recommended protocol for OTLP in production deployments. It’s more robust for structured log delivery compared to HTTP/JSON.
