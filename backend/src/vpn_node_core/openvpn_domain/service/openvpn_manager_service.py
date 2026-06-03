import logging
from pathlib import Path

from vpn_node_core.config import OpenVpnConfig
from vpn_node_core.openvpn_domain.domain.commands import (
    CreateOpenVpnUserCommand,
    DeleteOpenVpnUserCommand,
)
from vpn_node_core.openvpn_domain.domain.provision_result import (
    DeleteResult,
    HealthStatus,
    ProvisionResult,
)
from vpn_node_core.openvpn_domain.service.easyrsa_service import EasyRsaService
from vpn_node_core.openvpn_domain.service.ovpn_builder_service import build_ovpn_config

LOGGER = logging.getLogger(__name__)


class OpenVpnManagerService:
    """Data-plane service: certificates, CCD, and .ovpn profile assembly."""

    def __init__(self, config: OpenVpnConfig, easyrsa: EasyRsaService | None = None) -> None:
        self._config = config
        self._easyrsa = easyrsa or EasyRsaService(config)

    def _remote(self, command: CreateOpenVpnUserCommand) -> tuple[str, int, str]:
        remote = command.remote
        host = (remote.server_host if remote else None) or self._config.server_host
        port = (remote.server_port if remote else None) or self._config.server_port
        proto = (remote.proto if remote else None) or self._config.server_proto
        return host, port, proto

    async def create_user(self, command: CreateOpenVpnUserCommand) -> ProvisionResult:
        cn = command.common_name
        idempotent = await self._easyrsa.client_exists(cn)
        cert = await self._easyrsa.create_client(cn)
        await self._ensure_ccd(cn)

        host, port, proto = self._remote(command)
        ovpn = build_ovpn_config(
            ca_cert=cert.ca_cert,
            client_cert=cert.client_cert,
            client_key=cert.client_key,
            server_host=host,
            server_port=port,
            proto=proto,
            common_name=cn,
        )
        return ProvisionResult(ovpn_config=ovpn, common_name=cn, idempotent=idempotent)

    async def delete_user(self, command: DeleteOpenVpnUserCommand) -> DeleteResult:
        await self._easyrsa.revoke_client(command.common_name)
        await self._remove_ccd(command.common_name)
        return DeleteResult(common_name=command.common_name, revoked=True)

    async def health(self) -> HealthStatus:
        running = True
        if not self._config.mock_mode:
            try:
                proc = await self._easyrsa._run_command(  # noqa: SLF001
                    ["systemctl", "is-active", self._config.openvpn_service]
                )
                running = proc.strip() == "active"
            except Exception as exc:
                LOGGER.warning("OpenVPN service check failed: %s", exc)
                running = False

        return HealthStatus(
            status="healthy" if running else "degraded",
            openvpn_running=running,
            mock_mode=self._config.mock_mode,
            active_clients=await self._easyrsa.active_client_count(),
        )

    async def _ensure_ccd(self, common_name: str) -> None:
        if self._config.mock_mode:
            return
        ccd_path = Path(self._config.ccd_dir) / common_name
        ccd_path.parent.mkdir(parents=True, exist_ok=True)
        if not ccd_path.exists():
            ccd_path.write_text("# managed by openvpn-node\n")

    async def _remove_ccd(self, common_name: str) -> None:
        if self._config.mock_mode:
            return
        ccd_path = Path(self._config.ccd_dir) / common_name
        if ccd_path.exists():
            ccd_path.unlink()
