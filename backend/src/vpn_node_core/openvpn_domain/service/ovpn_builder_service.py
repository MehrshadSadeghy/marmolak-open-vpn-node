def build_ovpn_config(
    *,
    ca_cert: str,
    client_cert: str,
    client_key: str,
    server_host: str,
    server_port: int,
    proto: str,
    common_name: str,
) -> str:
    return (
        "client\n"
        "dev tun\n"
        f"proto {proto}\n"
        f"remote {server_host} {server_port}\n"
        "resolv-retry infinite\n"
        "nobind\n"
        "persist-key\n"
        "persist-tun\n"
        "remote-cert-tls server\n"
        "cipher AES-256-GCM\n"
        "auth SHA256\n"
        "verb 3\n"
        f"# common_name: {common_name}\n"
        "<ca>\n"
        f"{ca_cert.strip()}\n"
        "</ca>\n"
        "<cert>\n"
        f"{client_cert.strip()}\n"
        "</cert>\n"
        "<key>\n"
        f"{client_key.strip()}\n"
        "</key>\n"
    )
