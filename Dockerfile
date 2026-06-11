FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl ca-certificates bash curl \
    && curl -fsSL https://github.com/OpenVPN/easy-rsa/releases/download/v3.1.7/EasyRSA-3.1.7.tgz \
        | tar -xz -C /opt \
    && ln -sf /opt/EasyRSA-3.1.7/easyrsa /usr/local/bin/easyrsa \
    && ln -sf /opt/EasyRSA-3.1.7 /usr/share/easy-rsa \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY backend ./backend

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/backend/src
ENV PYTHONUNBUFFERED=1
ENV OPENVPN_NODE_ENVIRONMENT=docker

EXPOSE 8090

CMD ["python", "-m", "vpn_node_core"]
