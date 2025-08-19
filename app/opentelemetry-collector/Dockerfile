# Source gets built and pushed to the container registry from here:
# https://github.com/AgentOps-AI/opentelemetry-collector-contrib


# `builder` creates config files
FROM python:3.12-slim AS builder

WORKDIR /app
COPY builder ./builder
COPY config ./config

RUN pip install -e builder
RUN mkdir -p out
RUN python -m builder generate_configs -o /app/out


# collector service
FROM agentopsai/otelcontribcol:latest

COPY --from=builder /app/out/* /etc/config/

EXPOSE 1888 8888 8889 13133 4317 4318 55679

# `otelcollector` merges multiple config files internally
CMD ["--config=/etc/config/base.yaml", "--config=/etc/config/processors.yaml"]