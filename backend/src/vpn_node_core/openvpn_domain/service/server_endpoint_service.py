import json
import logging
import re
from pathlib import Path

from vpn_node_core.config import OpenVpnConfig
from vpn_node_core.openvpn_domain.domain.endpoint_result import ApplyEndpointResult
from vpn_node_core.openvpn_domain.service.easyrsa_service import EasyRsaService

LOGGER = logging.getLogger(__name__)

_SERVER_CONF_FALLBACKS = (
    "/host/etc/openvpn/server/server.conf",
    "/etc/openvpn/server/server.conf",
)


def resolve_server_conf_path(configured_path: str) -> Path:
    candidates = [configured_path, *_SERVER_CONF_FALLBACKS]
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        path = Path(candidate)
        if path.is_file():
            return path
    raise RuntimeError(
        "OpenVPN server config not found. Tried: "
        + ", ".join(seen)
        + ". Mount the host filesystem (e.g. /:/host:rslave) or set OPENVPN_SERVER_CONF_PATH."
    )


def update_server_conf_text(content: str, port: int, proto: str) -> str:
    proto = proto.lower()
    if proto not in ("udp", "tcp"):
        raise ValueError("proto must be udp or tcp")

    lines = content.splitlines()
    new_lines: list[str] = []
    found_port = False
    found_proto = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("port "):
            new_lines.append(f"port {port}")
            found_port = True
        elif stripped.startswith("proto "):
            new_lines.append(f"proto {proto}")
            found_proto = True
        elif stripped.startswith("explicit-exit-notify") or stripped.startswith("# explicit-exit-notify"):
            if proto == "udp":
                new_lines.append("explicit-exit-notify 1")
            elif not stripped.startswith("#"):
                new_lines.append(f"# {stripped}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if not found_port:
        new_lines.insert(0, f"port {port}")
    if not found_proto:
        insert_at = 1 if found_port else 0
        new_lines.insert(insert_at, f"proto {proto}")

    result = "\n".join(new_lines)
    if not result.endswith("\n"):
        result += "\n"
    return result


def update_env_file_text(content: str, port: int, proto: str) -> str:
    updates = {
        "SERVER_PORT": str(port),
        "SERVER_PROTO": proto.lower(),
    }
    lines = content.splitlines()
    seen: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        matched = False
        for key, value in updates.items():
            if re.match(rf"^{re.escape(key)}=", line):
                new_lines.append(f"{key}={value}")
                seen.add(key)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in seen:
            new_lines.append(f"{key}={value}")

    result = "\n".join(new_lines)
    if not result.endswith("\n"):
        result += "\n"
    return result


class ServerEndpointService:
    """Applies OpenVPN listen port/protocol on the host."""

    def __init__(self, config: OpenVpnConfig, easyrsa: EasyRsaService) -> None:
        self._config = config
        self._easyrsa = easyrsa

    async def apply_endpoint(self, port: int, proto: str) -> ApplyEndpointResult:
        proto = proto.lower()
        if proto not in ("udp", "tcp"):
            raise ValueError("proto must be udp or tcp")
        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535")

        previous_port = self._config.server_port
        previous_proto = self._config.server_proto

        server_conf_updated = False
        firewall_rule_added = False
        env_file_updated = False
        openvpn_running = True

        if self._config.mock_mode:
            self._update_runtime_config(port, proto)
            await self._persist_state(port, proto)
            return ApplyEndpointResult(
                port=port,
                proto=proto,
                openvpn_running=True,
                server_conf_updated=False,
                firewall_rule_added=False,
                env_file_updated=False,
                previous_port=previous_port,
                previous_proto=previous_proto,
            )

        conf_path = resolve_server_conf_path(self._config.server_conf_path)

        updated_conf = update_server_conf_text(conf_path.read_text(encoding="utf-8"), port, proto)
        conf_path.write_text(updated_conf, encoding="utf-8")
        server_conf_updated = True

        firewall_rule_added = await self._ensure_firewall(port, proto)
        env_file_updated = self._update_dotenv_files(port, proto)
        await self._restart_openvpn()
        self._update_runtime_config(port, proto)
        await self._persist_state(port, proto)
        openvpn_running = await self._check_openvpn_running()

        return ApplyEndpointResult(
            port=port,
            proto=proto,
            openvpn_running=openvpn_running,
            server_conf_updated=server_conf_updated,
            firewall_rule_added=firewall_rule_added,
            env_file_updated=env_file_updated,
            previous_port=previous_port,
            previous_proto=previous_proto,
        )

    def _update_runtime_config(self, port: int, proto: str) -> None:
        self._config.server_port = port
        self._config.server_proto = proto.lower()

    async def _persist_state(self, port: int, proto: str) -> None:
        state_path = Path(self._config.endpoint_state_path)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps({"server_port": port, "server_proto": proto.lower()}, indent=2) + "\n",
            encoding="utf-8",
        )

    def _update_dotenv_files(self, port: int, proto: str) -> bool:
        updated_any = False
        for path_str in self._config.dotenv_paths:
            path = Path(path_str)
            if not path.is_file():
                continue
            try:
                path.write_text(
                    update_env_file_text(path.read_text(encoding="utf-8"), port, proto),
                    encoding="utf-8",
                )
                updated_any = True
            except OSError as exc:
                LOGGER.warning("Failed to update dotenv file %s: %s", path, exc)
        return updated_any

    async def _ensure_firewall(self, port: int, proto: str) -> bool:
        try:
            status = await self._easyrsa._run_command(["ufw", "status"])  # noqa: SLF001
        except (RuntimeError, FileNotFoundError):
            return False

        if "Status: active" not in status:
            return False

        try:
            await self._easyrsa._run_command(["ufw", "allow", f"{port}/{proto}"])  # noqa: SLF001
            await self._easyrsa._run_command(["ufw", "reload"])  # noqa: SLF001
            return True
        except RuntimeError as exc:
            LOGGER.warning("ufw update failed: %s", exc)
            return False

    async def _restart_openvpn(self) -> None:
        await self._easyrsa._run_command(  # noqa: SLF001
            ["systemctl", "restart", self._config.openvpn_service]
        )

    async def _check_openvpn_running(self) -> bool:
        try:
            proc = await self._easyrsa._run_command(  # noqa: SLF001
                ["systemctl", "is-active", self._config.openvpn_service]
            )
            return proc.strip() == "active"
        except RuntimeError:
            return False
