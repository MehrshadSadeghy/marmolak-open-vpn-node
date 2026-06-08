import json
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8090
    title: str = "OpenVPN Node"
    version: str = "0.1.0"


class OpenVpnConfig(BaseModel):
    node_api_secret: str = "change-me-node-secret"
    mock_mode: bool = True
    easy_rsa_path: str = "/etc/openvpn/easy-rsa"
    easyrsa_bin_path: str | None = None
    ca_path: str = "/etc/openvpn/easy-rsa/pki/ca.crt"
    ccd_dir: str = "/etc/openvpn/ccd"
    pki_dir: str = "/etc/openvpn/easy-rsa/pki"
    issued_dir: str = "/etc/openvpn/easy-rsa/pki/issued"
    private_dir: str = "/etc/openvpn/easy-rsa/pki/private"
    server_host: str = "vpn.example.com"
    server_port: int = 1194
    server_proto: str = "udp"
    openvpn_service: str = "openvpn-server@server"
    server_conf_path: str = "/etc/openvpn/server/server.conf"
    endpoint_state_path: str = "/etc/openvpn/node-endpoint.json"
    status_log_path: str = "/var/log/openvpn/openvpn-status.log"
    dotenv_paths: list[str] = Field(
        default_factory=lambda: [
            "/etc/openvpn/open-node.env",
            "/host-env/.env",
        ]
    )


class Config(BaseModel):
    api: APIConfig
    openvpn: OpenVpnConfig = Field(default_factory=OpenVpnConfig)


def backend_root_directory() -> Path:
    return Path(__file__).resolve().parents[2]


def _apply_env_overrides(data: dict) -> None:
    openvpn = data.setdefault("openvpn", {})
    if secret := os.getenv("NODE_API_SECRET"):
        openvpn["node_api_secret"] = secret
    if mock := os.getenv("MOCK_MODE"):
        openvpn["mock_mode"] = mock.lower() in ("1", "true", "yes")
    if host := os.getenv("SERVER_HOST"):
        openvpn["server_host"] = host
    if port := os.getenv("SERVER_PORT"):
        openvpn["server_port"] = int(port)
    if proto := os.getenv("SERVER_PROTO"):
        openvpn["server_proto"] = proto
    if conf_path := os.getenv("OPENVPN_SERVER_CONF_PATH"):
        openvpn["server_conf_path"] = conf_path
    if state_path := os.getenv("OPENVPN_ENDPOINT_STATE_PATH"):
        openvpn["endpoint_state_path"] = state_path
    if dotenv_paths := os.getenv("OPENVPN_DOTENV_PATHS"):
        openvpn["dotenv_paths"] = [item.strip() for item in dotenv_paths.split(",") if item.strip()]
    if easyrsa_bin := os.getenv("EASYRSA_BIN_PATH"):
        openvpn["easyrsa_bin_path"] = easyrsa_bin
    if status_log := os.getenv("OPENVPN_STATUS_LOG_PATH"):
        openvpn["status_log_path"] = status_log


def _apply_endpoint_state_file(openvpn: dict) -> None:
    state_path = Path(openvpn.get("endpoint_state_path", "/etc/openvpn/node-endpoint.json"))
    if not state_path.is_file():
        return
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if port := data.get("server_port"):
        openvpn["server_port"] = int(port)
    if proto := data.get("server_proto"):
        openvpn["server_proto"] = str(proto).lower()


def load_config(environment: str | None = None) -> Config:
    backend = backend_root_directory()
    load_dotenv(backend / ".env")
    load_dotenv(backend.parent / ".env")

    env_name = environment or os.environ.get("OPENVPN_NODE_ENVIRONMENT", "config")
    path = backend / "config" / f"{env_name}.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    _apply_env_overrides(data)
    _apply_endpoint_state_file(data.setdefault("openvpn", {}))
    return Config(**data)
