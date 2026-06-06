import hashlib
import hmac
import time

from fastapi import HTTPException, Request

from vpn_node_core.config import OpenVpnConfig


def _sign_payload(secret: str, timestamp: str, method: str, path: str, body: bytes) -> str:
    message = f"{timestamp}{method.upper()}{path}".encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


async def verify_node_signature(request: Request, openvpn_config: OpenVpnConfig) -> None:
    """Validate HMAC headers for signed node routes."""
    x_node_timestamp = request.headers.get("X-Node-Timestamp")
    x_node_signature = request.headers.get("X-Node-Signature")

    if openvpn_config.mock_mode and not x_node_signature:
        return

    if not x_node_timestamp or not x_node_signature:
        raise HTTPException(status_code=401, detail="Missing node signature headers")

    try:
        ts = int(x_node_timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid timestamp") from exc

    if abs(time.time() - ts) > 300:
        raise HTTPException(status_code=401, detail="Request timestamp expired")

    body = await request.body()
    expected = _sign_payload(
        openvpn_config.node_api_secret,
        x_node_timestamp,
        request.method,
        request.url.path,
        body,
    )
    if not hmac.compare_digest(expected, x_node_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


def verify_node_signature_factory(openvpn_config: OpenVpnConfig):
    async def _verify(request: Request) -> None:
        await verify_node_signature(request, openvpn_config)

    return _verify
