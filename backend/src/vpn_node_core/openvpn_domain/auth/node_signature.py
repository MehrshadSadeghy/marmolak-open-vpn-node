import hashlib
import hmac
import time

from fastapi import Header, HTTPException, Request

from vpn_node_core.config import OpenVpnConfig


def _sign_payload(secret: str, timestamp: str, method: str, path: str, body: bytes) -> str:
    message = f"{timestamp}{method.upper()}{path}".encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify_node_signature_factory(openvpn_config: OpenVpnConfig):
    async def verify_node_signature(
        request: Request,
        x_node_timestamp: str | None = Header(default=None, alias="X-Node-Timestamp"),
        x_node_signature: str | None = Header(default=None, alias="X-Node-Signature"),
    ) -> None:
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

    return verify_node_signature
