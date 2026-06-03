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
    ca_path: str = "/etc/openvpn/easy-rsa/pki/ca.crt"
    ccd_dir: str = "/etc/openvpn/ccd"
    pki_dir: str = "/etc/openvpn/easy-rsa/pki"
    issued_dir: str = "/etc/openvpn/easy-rsa/pki/issued"
    private_dir: str = "/etc/openvpn/easy-rsa/pki/private"
    server_host: str = "vpn.example.com"
    server_port: int = 1194
    server_proto: str = "udp"
    openvpn_service: str = "openvpn-server@server"


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


def load_config(environment: str | None = None) -> Config:
    backend = backend_root_directory()
    load_dotenv(backend / ".env")
    load_dotenv(backend.parent / ".env")

    env_name = environment or os.environ.get("OPENVPN_NODE_ENVIRONMENT", "config")
    path = backend / "config" / f"{env_name}.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    _apply_env_overrides(data)
    return Config(**data)
