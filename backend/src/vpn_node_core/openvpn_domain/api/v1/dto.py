from pydantic import BaseModel, Field

from vpn_node_core.openvpn_domain.domain.commands import (
    CreateOpenVpnUserCommand,
    DeleteOpenVpnUserCommand,
    ServerRemoteConfig,
)
from vpn_node_core.openvpn_domain.domain.endpoint_result import ApplyEndpointResult
from vpn_node_core.openvpn_domain.domain.provision_result import (
    DeleteResult,
    HealthStatus,
    ProvisionResult,
)


class ServerConfigDTO(BaseModel):
    server_host: str | None = None
    server_port: int | None = None
    proto: str | None = None

    def to_domain(self) -> ServerRemoteConfig:
        return ServerRemoteConfig(
            server_host=self.server_host,
            server_port=self.server_port,
            proto=self.proto,
        )


class CreateOpenVpnRequestDTO(BaseModel):
    common_name: str = Field(min_length=1, max_length=255)
    server_config: ServerConfigDTO | None = None

    def to_command(self) -> CreateOpenVpnUserCommand:
        return CreateOpenVpnUserCommand(
            common_name=self.common_name,
            remote=self.server_config.to_domain() if self.server_config else None,
        )


class CreateOpenVpnResponseDTO(BaseModel):
    status: str = "success"
    ovpn_config: str
    common_name: str
    idempotent: bool = False

    @classmethod
    def from_result(cls, result: ProvisionResult) -> "CreateOpenVpnResponseDTO":
        return cls(
            ovpn_config=result.ovpn_config,
            common_name=result.common_name,
            idempotent=result.idempotent,
        )


class DeleteOpenVpnRequestDTO(BaseModel):
    common_name: str = Field(min_length=1, max_length=255)

    def to_command(self) -> DeleteOpenVpnUserCommand:
        return DeleteOpenVpnUserCommand(common_name=self.common_name)


class DeleteOpenVpnResponseDTO(BaseModel):
    status: str = "success"
    common_name: str
    revoked: bool = True

    @classmethod
    def from_result(cls, result: DeleteResult) -> "DeleteOpenVpnResponseDTO":
        return cls(common_name=result.common_name, revoked=result.revoked)


class HealthResponseDTO(BaseModel):
    status: str
    openvpn_running: bool
    mock_mode: bool
    active_clients: int
    server_port: int | None = None
    server_proto: str | None = None

    @classmethod
    def from_status(cls, status: HealthStatus, *, server_port: int | None = None, server_proto: str | None = None) -> "HealthResponseDTO":
        return cls(
            status=status.status,
            openvpn_running=status.openvpn_running,
            mock_mode=status.mock_mode,
            active_clients=status.active_clients,
            server_port=server_port,
            server_proto=server_proto,
        )


class ApplyEndpointRequestDTO(BaseModel):
    port: int = Field(ge=1, le=65535)
    proto: str = Field(min_length=3, max_length=3)


class ApplyEndpointResponseDTO(BaseModel):
    status: str = "success"
    port: int
    proto: str
    openvpn_running: bool
    server_conf_updated: bool
    firewall_rule_added: bool
    env_file_updated: bool
    previous_port: int | None = None
    previous_proto: str | None = None

    @classmethod
    def from_result(cls, result: ApplyEndpointResult) -> "ApplyEndpointResponseDTO":
        return cls(
            port=result.port,
            proto=result.proto,
            openvpn_running=result.openvpn_running,
            server_conf_updated=result.server_conf_updated,
            firewall_rule_added=result.firewall_rule_added,
            env_file_updated=result.env_file_updated,
            previous_port=result.previous_port,
            previous_proto=result.previous_proto,
        )
