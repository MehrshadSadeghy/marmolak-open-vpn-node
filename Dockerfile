FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl ca-certificates bash \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY backend ./backend

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/backend/src
ENV PYTHONUNBUFFERED=1
ENV OPENVPN_NODE_ENVIRONMENT=docker

EXPOSE 8090

CMD ["python", "-m", "vpn_node_core"]
