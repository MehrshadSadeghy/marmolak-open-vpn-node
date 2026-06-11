def build_ovpn_config(
    *,
    ca_cert: str,
    client_cert: str,
    client_key: str,
    server_host: str,
    server_port: int,
    proto: str,
    common_name: str,
    tls_crypt_key: str | None = None,
) -> str:
    proto = proto.lower()
    if proto not in ("udp", "tcp"):
        raise ValueError("proto must be udp or tcp")
    header_lines = [
        "client",
        "dev tun",
        "nobind",
        "persist-key",
        "persist-tun",
        "remote-cert-tls server",
        "data-ciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305",
        "compat-mode 2.6.0",
        "disable-dco",
        "tun-mtu 1400",
        "mssfix 1360",
        "verb 3",
        f"remote {server_host} {server_port}",
        f"proto {proto}",
        f"# common_name: {common_name}",
    ]

    blocks = [
        "\n".join(header_lines),
        "<ca>\n" + f"{ca_cert.strip()}\n" + "</ca>",
        "<cert>\n" + f"{client_cert.strip()}\n" + "</cert>",
        "<key>\n" + f"{client_key.strip()}\n" + "</key>",
    ]
    if tls_crypt_key:
        blocks.append("<tls-crypt>\n" + f"{tls_crypt_key.strip()}\n" + "</tls-crypt>")
    return "\n".join(blocks) + "\n"
