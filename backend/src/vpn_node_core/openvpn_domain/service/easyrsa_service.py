from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
from pathlib import Path

from vpn_node_core.config import OpenVpnConfig
from vpn_node_core.openvpn_domain.domain.client_certificate import ClientCertificate

LOGGER = logging.getLogger(__name__)

BUNDLED_EASYRSA_CANDIDATES = (
    "/usr/share/easy-rsa/easyrsa",
    "/usr/share/easy-rsa/easyrsa3/easyrsa",
)


class EasyRsaService:
    """Manages EasyRSA PKI on the VPN server host."""

    def __init__(self, config: OpenVpnConfig) -> None:
        self._config = config
        self._mock_store: dict[str, ClientCertificate] = {}
        self._revoked: set[str] = set()

    def _resolve_easyrsa_bin(self) -> Path | None:
        if self._config.easyrsa_bin_path:
            configured = Path(self._config.easyrsa_bin_path)
            if configured.is_file():
                return configured

        mounted = Path(self._config.easy_rsa_path) / "easyrsa"
        if mounted.is_file():
            return mounted

        for candidate in BUNDLED_EASYRSA_CANDIDATES:
            path = Path(candidate)
            if path.is_file():
                return path
        return None

    def check_pki_ready(self) -> tuple[bool, str | None]:
        if self._config.mock_mode:
            return True, None

        easyrsa_bin = self._resolve_easyrsa_bin()
        if easyrsa_bin is None:
            return False, (
                f"EasyRSA script missing under {self._config.easy_rsa_path} "
                f"and bundled paths ({', '.join(BUNDLED_EASYRSA_CANDIDATES)})"
            )
        if shutil.which("openssl") is None:
            return False, "openssl binary not found in container PATH"

        ca_path = Path(self._config.ca_path)
        if not ca_path.is_file():
            return False, (
                f"CA certificate missing: {ca_path}. "
                "Run scripts/setup-easyrsa-host.sh on the VPN server."
            )

        issued_dir = Path(self._config.issued_dir)
        private_dir = Path(self._config.private_dir)
        if not issued_dir.is_dir():
            return False, f"Issued certs directory missing: {issued_dir}"
        if not private_dir.is_dir():
            return False, f"Private keys directory missing: {private_dir}"
        return True, None

    async def create_client(self, common_name: str) -> ClientCertificate:
        if common_name in self._revoked:
            self._revoked.discard(common_name)

        if self._config.mock_mode:
            if common_name in self._mock_store:
                return self._mock_store[common_name]
            cert = self._mock_certificate(common_name)
            self._mock_store[common_name] = cert
            return cert

        ready, error = self.check_pki_ready()
        if not ready:
            raise RuntimeError(error or "EasyRSA PKI is not ready")

        await self._run_easyrsa(["--batch", "build-client-full", common_name, "nopass"])
        return await self._read_client_files(common_name)

    async def revoke_client(self, common_name: str) -> None:
        if self._config.mock_mode:
            self._mock_store.pop(common_name, None)
            self._revoked.add(common_name)
            return

        cert_path = Path(self._config.issued_dir) / f"{common_name}.crt"
        if not cert_path.exists():
            LOGGER.info("Certificate already absent: %s", common_name)
            return

        await self._run_easyrsa(["--batch", "revoke", common_name, "yes"])
        await self._run_easyrsa(["gen-crl"])
        await self._run_command(
            ["cp", f"{self._config.pki_dir}/crl.pem", "/etc/openvpn/crl.pem"]
        )
        await self._run_command(["systemctl", "reload", self._config.openvpn_service])

    async def client_exists(self, common_name: str) -> bool:
        if self._config.mock_mode:
            return common_name in self._mock_store and common_name not in self._revoked

        cert_path = Path(self._config.issued_dir) / f"{common_name}.crt"
        return cert_path.exists() and common_name not in self._revoked

    async def active_client_count(self) -> int:
        if self._config.mock_mode:
            return len(self._mock_store)
        if not Path(self._config.issued_dir).exists():
            return 0
        return len(list(Path(self._config.issued_dir).glob("*.crt")))

    async def _read_client_files(self, common_name: str) -> ClientCertificate:
        try:
            ca_cert = Path(self._config.ca_path).read_text(encoding="utf-8")
            client_cert = (Path(self._config.issued_dir) / f"{common_name}.crt").read_text(encoding="utf-8")
            client_key = (Path(self._config.private_dir) / f"{common_name}.key").read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise RuntimeError(f"Certificate files missing after EasyRSA build: {exc}") from exc
        except OSError as exc:
            raise RuntimeError(f"Cannot read certificate files: {exc}") from exc
        return ClientCertificate(
            common_name=common_name,
            ca_cert=ca_cert,
            client_cert=client_cert,
            client_key=client_key,
        )

    async def _run_easyrsa(self, args: list[str]) -> str:
        easyrsa = self._resolve_easyrsa_bin()
        if easyrsa is None:
            raise RuntimeError("EasyRSA binary is not available")

        pki_dir = self._config.pki_dir
        command = ["bash", str(easyrsa), f"--pki={pki_dir}", *args]
        cwd = str(easyrsa.parent)
        env = os.environ.copy()
        env.setdefault("EASYRSA_PKI", pki_dir)
        return await self._run_command(command, cwd=cwd, env=env)

    async def _run_command(
        self,
        command: list[str],
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> str:
        def _execute() -> subprocess.CompletedProcess[str]:
            try:
                return subprocess.run(
                    command,
                    cwd=cwd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError as exc:
                raise RuntimeError(f"Command not found: {command[0]} ({exc})") from exc
            except OSError as exc:
                raise RuntimeError(f"Failed to run command {command!r}: {exc}") from exc

        try:
            process = await asyncio.to_thread(_execute)
        except RuntimeError:
            raise
        if process.returncode != 0:
            detail = process.stderr.strip() or process.stdout.strip() or f"exit code {process.returncode}"
            raise RuntimeError(detail)
        return process.stdout

    def _mock_certificate(self, common_name: str) -> ClientCertificate:
        return ClientCertificate(
            common_name=common_name,
            ca_cert="-----BEGIN CERTIFICATE-----\nMOCK-CA\n-----END CERTIFICATE-----",
            client_cert=f"-----BEGIN CERTIFICATE-----\nMOCK-{common_name}\n-----END CERTIFICATE-----",
            client_key=f"-----BEGIN PRIVATE KEY-----\nMOCK-KEY-{common_name}\n-----END PRIVATE KEY-----",
        )
