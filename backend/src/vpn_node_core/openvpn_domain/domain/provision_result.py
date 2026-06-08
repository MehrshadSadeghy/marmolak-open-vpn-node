from pydantic import BaseModel


class ProvisionResult(BaseModel):
    ovpn_config: str
    common_name: str
    idempotent: bool = False


class DeleteResult(BaseModel):
    common_name: str
    revoked: bool = True


class HealthStatus(BaseModel):
    status: str
    openvpn_running: bool
    mock_mode: bool
    active_clients: int
    easyrsa_ready: bool = True
    easyrsa_error: str | None = None
