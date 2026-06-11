from vpn_node_core.openvpn_domain.service.ovpn_builder_service import build_ovpn_config


def test_build_ovpn_config_uses_single_udp_1433_remote():
    ovpn = build_ovpn_config(
        ca_cert="-----BEGIN CERTIFICATE-----\nCA\n-----END CERTIFICATE-----",
        client_cert="-----BEGIN CERTIFICATE-----\nCRT\n-----END CERTIFICATE-----",
        client_key="-----BEGIN PRIVATE KEY-----\nKEY\n-----END PRIVATE KEY-----",
        server_host="144.31.167.163",
        server_port=1433,
        proto="udp",
        common_name="tg-123",
    )

    assert "remote 144.31.167.163 1433" in ovpn
    assert "proto udp" in ovpn
    assert "tun-mtu 1400" in ovpn
    assert "data-ciphers AES-256-GCM:AES-128-GCM" in ovpn
    assert "disable-dco" in ovpn
    assert "remote-random" not in ovpn
    assert "1194" not in ovpn
    assert "443" not in ovpn


def test_build_ovpn_config_respects_endpoint_override():
    ovpn = build_ovpn_config(
        ca_cert="ca",
        client_cert="crt",
        client_key="key",
        server_host="10.0.0.1",
        server_port=1433,
        proto="udp",
        common_name="tg-456",
    )

    assert "remote 10.0.0.1 1433" in ovpn
    assert "proto udp" in ovpn
