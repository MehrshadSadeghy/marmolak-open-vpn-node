from pathlib import Path

import pytest

from vpn_node_core.openvpn_domain.service.server_endpoint_service import (
    resolve_server_conf_path,
    update_env_file_text,
    update_server_conf_text,
)


def test_update_server_conf_tcp_443():
    content = """port 1194
proto udp
explicit-exit-notify 1
"""
    updated = update_server_conf_text(content, 443, "tcp")
    assert "port 443" in updated
    assert "proto tcp" in updated
    assert "# explicit-exit-notify 1" in updated


def test_update_server_conf_udp_restores_exit_notify():
    content = """port 443
proto tcp
# explicit-exit-notify 1
"""
    updated = update_server_conf_text(content, 1194, "udp")
    assert "port 1194" in updated
    assert "proto udp" in updated
    assert "explicit-exit-notify 1" in updated
    assert "# explicit-exit-notify 1" not in updated


def test_resolve_server_conf_path_uses_configured_file(tmp_path: Path):
    conf = tmp_path / "server.conf"
    conf.write_text("port 1194\n", encoding="utf-8")
    assert resolve_server_conf_path(str(conf)) == conf


def test_resolve_server_conf_path_raises_when_missing():
    with pytest.raises(RuntimeError, match="OpenVPN server config not found"):
        resolve_server_conf_path("/definitely/missing/server.conf")


def test_update_env_file_text():
    content = """API_PORT=8090
SERVER_PORT=1194
SERVER_PROTO=udp
"""
    updated = update_env_file_text(content, 443, "tcp")
    assert "SERVER_PORT=443" in updated
    assert "SERVER_PROTO=tcp" in updated
    assert "API_PORT=8090" in updated
