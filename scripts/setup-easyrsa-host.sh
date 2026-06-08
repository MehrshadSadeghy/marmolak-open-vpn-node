#!/usr/bin/env bash
# Prepare EasyRSA PKI on the VPN host for openvpn-node.
#
# Run once on the VPN server (as root):
#   sudo ./scripts/setup-easyrsa-host.sh
#
# Requires: openvpn, easy-rsa, openssl

set -euo pipefail

EASYRSA_DIR="/etc/openvpn/easy-rsa"
PKI_DIR="${EASYRSA_DIR}/pki"
CA_PATH="${PKI_DIR}/ca.crt"
EASYRSA_BIN=""

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
  apt-get update
  apt-get install -y openssl
fi

if ! command -v easyrsa >/dev/null 2>&1; then
  apt-get update
  apt-get install -y easy-rsa openvpn
fi

for candidate in /usr/share/easy-rsa/easyrsa /usr/share/easy-rsa/easyrsa3/easyrsa "${EASYRSA_DIR}/easyrsa"; do
  if [[ -f "${candidate}" ]]; then
    EASYRSA_BIN="${candidate}"
    break
  fi
done

if [[ -z "${EASYRSA_BIN}" ]]; then
  echo "Could not locate easyrsa binary after installing easy-rsa package." >&2
  exit 1
fi

mkdir -p "${EASYRSA_DIR}" "${PKI_DIR}/issued" "${PKI_DIR}/private" "${PKI_DIR}/reqs"
chmod 700 "${PKI_DIR}/private"

if [[ -f "${CA_PATH}" ]]; then
  echo "PKI already initialized: ${CA_PATH}"
else
  echo "Initializing EasyRSA PKI at ${PKI_DIR}"
  bash "${EASYRSA_BIN}" --pki="${PKI_DIR}" init-pki
  bash "${EASYRSA_BIN}" --pki="${PKI_DIR}" --batch build-ca nopass
  echo "CA created at ${CA_PATH}"
fi

if ! systemctl is-active --quiet openvpn-server@server; then
  echo "Starting OpenVPN service..."
  systemctl enable openvpn-server@server
  systemctl start openvpn-server@server || true
fi

echo
echo "Next steps:"
echo "  1. cd ~/vpn/open-node/marmolak-open-vpn-node/core   # adjust path"
echo "  2. Ensure MOCK_MODE=false in .env"
echo "  3. docker compose up --build -d"
echo "  4. curl http://127.0.0.1:8090/node/health"
