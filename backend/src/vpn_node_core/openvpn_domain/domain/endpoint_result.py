from pydantic import BaseModel


class ApplyEndpointResult(BaseModel):
    port: int
    proto: str
    openvpn_running: bool
    server_conf_updated: bool
    firewall_rule_added: bool
    env_file_updated: bool
    previous_port: int | None = None
    previous_proto: str | None = None
