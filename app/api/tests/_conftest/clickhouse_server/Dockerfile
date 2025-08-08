FROM clickhouse/clickhouse-server:24.12

# Set environment variables
# TODO I dont think user/pass actually modify the install, but they do reference
# the actual values we see inside the container
ENV CLICKHOUSE_USER=default
ENV CLICKHOUSE_PASSWORD=clickhouse
ENV CLICKHOUSE_DB=otel_2

# Expose ports
EXPOSE 8123
EXPOSE 9000

# Add healthcheck
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8123/ping || exit 1

