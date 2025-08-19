FROM grafana/grafana:latest

USER root

# Install ClickHouse plugin
RUN grafana-cli plugins install vertamedia-clickhouse-datasource

# Change back to grafana user
USER grafana