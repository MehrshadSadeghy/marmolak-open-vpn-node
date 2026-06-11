from pathlib import Path

import pytest

from vpn_node_core.config import OpenVpnConfig
from vpn_node_core.openvpn_domain.service.easyrsa_service import EasyRsaService


def _service(tmp_path: Path, **overrides) -> EasyRsaService:
    pki = tmp_path / "pki"
    (pki / "issued").mkdir(parents=True)
    (pki / "private").mkdir(parents=True)
    config = OpenVpnConfig(
        mock_mode=False,
        easy_rsa_path=str(tmp_path),
        pki_dir=str(pki),
        ca_path=str(pki / "ca.crt"),
        issued_dir=str(pki / "issued"),
        private_dir=str(pki / "private"),
        **overrides,
    )
    return EasyRsaService(config)


def test_check_pki_ready_uses_bundled_easyrsa_when_mount_has_only_pki(tmp_path: Path):
    bundled = Path("/usr/share/easy-rsa/easyrsa")
    if not bundled.is_file():
        pytest.skip("easy-rsa package not installed in test environment")

    (tmp_path / "pki" / "ca.crt").write_text("ca", encoding="utf-8")
    service = _service(tmp_path)

    ready, error = service.check_pki_ready()

    assert ready is True
    assert error is None
    assert service._resolve_easyrsa_bin() == bundled


def test_check_pki_ready_reports_missing_ca(tmp_path: Path):
    bundled = Path("/usr/share/easy-rsa/easyrsa")
    if not bundled.is_file():
        pytest.skip("easy-rsa package not installed in test environment")

    service = _service(tmp_path)

    ready, error = service.check_pki_ready()

    assert ready is False
    assert error is not None
    assert "CA certificate missing" in error


@pytest.mark.asyncio
async def test_revoke_client_uses_easyrsa_batch_without_invalid_reason(tmp_path: Path, monkeypatch):
    service = EasyRsaService(
        OpenVpnConfig(
            mock_mode=False,
            easy_rsa_path=str(tmp_path),
            pki_dir=str(tmp_path / "pki"),
            ca_path=str(tmp_path / "pki" / "ca.crt"),
            issued_dir=str(tmp_path / "pki" / "issued"),
            private_dir=str(tmp_path / "pki" / "private"),
        )
    )
    issued = tmp_path / "pki" / "issued"
    issued.mkdir(parents=True)
    (issued / "9149049423.crt").write_text("cert", encoding="utf-8")
    calls: list[list[str]] = []

    async def fake_run_easyrsa(args: list[str]) -> str:
        calls.append(args)
        return ""

    async def fake_run_command(command: list[str], **kwargs) -> str:
        return ""

    monkeypatch.setattr(service, "_run_easyrsa", fake_run_easyrsa)
    monkeypatch.setattr(service, "_run_command", fake_run_command)

    await service.revoke_client("9149049423")

    assert calls[0] == ["--batch", "revoke", "9149049423"]
