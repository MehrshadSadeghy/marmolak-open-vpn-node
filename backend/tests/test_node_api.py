import hashlib
import hmac
import json
import time

import pytest
from httpx import ASGITransport, AsyncClient

from vpn_node_core.container import AppContainer
from vpn_node_core.core.manager.api_manager import APIManager
from vpn_node_core.openvpn_domain.api.v1.router import router


def _signed_headers(*, secret: str, method: str, path: str, payload: dict) -> tuple[bytes, dict]:
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    message = f"{timestamp}{method.upper()}{path}".encode() + body
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Node-Timestamp": timestamp,
        "X-Node-Signature": signature,
    }
    return body, headers


@pytest.fixture
async def client():
    container = AppContainer()
    api = APIManager(
        api_config=container.get_config().api,
        container=container,
        routers=[router],
    )
    await api.setup()
    assert api._app is not None
    transport = ASGITransport(app=api._app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/node/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["mock_mode"] is True


@pytest.mark.asyncio
async def test_create_with_hmac_signature(client: AsyncClient):
    container = AppContainer()
    secret = container.get_config().openvpn.node_api_secret
    path = "/node/vpn/openvpn/create"
    payload = {
        "common_name": "tg-8322619451",
        "server_config": {
            "server_host": "144.31.167.163",
            "server_port": 1194,
            "proto": "udp",
        },
    }
    body, headers = _signed_headers(
        secret=secret,
        method="POST",
        path=path,
        payload=payload,
    )
    response = await client.post(path, content=body, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "BEGIN CERTIFICATE" in data["ovpn_config"]


@pytest.mark.asyncio
async def test_create_and_delete_openvpn_user(client: AsyncClient):
    create = await client.post(
        "/node/vpn/openvpn/create",
        json={"common_name": "tg-12345"},
    )
    assert create.status_code == 200
    data = create.json()
    assert data["status"] == "success"
    assert "BEGIN CERTIFICATE" in data["ovpn_config"]
    assert data["idempotent"] is False

    create_again = await client.post(
        "/node/vpn/openvpn/create",
        json={"common_name": "tg-12345"},
    )
    assert create_again.json()["idempotent"] is True

    delete = await client.post(
        "/node/vpn/openvpn/delete",
        json={"common_name": "tg-12345"},
    )
    assert delete.status_code == 200
    assert delete.json()["status"] == "success"
