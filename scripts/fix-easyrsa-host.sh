#!/usr/bin/env bash
# Fix "EasyRSA script missing: /etc/openvpn/easy-rsa/easyrsa" on the VPN host.
#
# Run on the OpenVPN server (as root):
#   sudo ./scripts/fix-easyrsa-host.sh
#
# Then rebuild/restart openvpn-node:
#   cd ~/vpn/open-node/marmolak-open-vpn-node/core   # adjust path
#   docker compose up --build -d
#   curl http://127.0.0.1:8090/node/health

set -euo pipefail

EASYRSA_DIR="/etc/openvpn/easy-rsa"
PKI_DIR="${EASYRSA_DIR}/pki"
SOURCE_DIR="/usr/share/easy-rsa"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

echo "==> Installing packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq easy-rsa openvpn openssl

if [[ ! -f "${SOURCE_DIR}/easyrsa" ]]; then
  echo "easyrsa not found at ${SOURCE_DIR}/easyrsa after install." >&2
  exit 1
fi

echo "==> Preparing ${EASYRSA_DIR}..."
mkdir -p "${EASYRSA_DIR}"

PKI_BACKUP=""
if [[ -d "${PKI_DIR}" ]]; then
  PKI_BACKUP="$(mktemp -d)"
  cp -a "${PKI_DIR}/." "${PKI_BACKUP}/"
  echo "Backed up existing PKI to ${PKI_BACKUP}"
fi

echo "==> Installing EasyRSA tools into ${EASYRSA_DIR}..."
cp -a "${SOURCE_DIR}/." "${EASYRSA_DIR}/"
chmod +x "${EASYRSA_DIR}/easyrsa"

if [[ -n "${PKI_BACKUP}" ]]; then
  rm -rf "${PKI_DIR}"
  mkdir -p "${PKI_DIR}"
  cp -a "${PKI_BACKUP}/." "${PKI_DIR}/"
  rm -rf "${PKI_BACKUP}"
fi

mkdir -p "${PKI_DIR}/issued" "${PKI_DIR}/private" "${PKI_DIR}/reqs"
chmod 700 "${PKI_DIR}/private"

if [[ ! -f "${PKI_DIR}/ca.crt" ]]; then
  echo "==> Initializing PKI (no CA found)..."
  cd "${EASYRSA_DIR}"
  ./easyrsa init-pki
  ./easyrsa --batch build-ca nopass
else
  echo "==> Existing CA found: ${PKI_DIR}/ca.crt"
fi

if [[ ! -f "${EASYRSA_DIR}/easyrsa" ]]; then
  echo "Failed to install easyrsa script." >&2
  exit 1
fi

echo "==> Starting OpenVPN..."
systemctl enable openvpn-server@server 2>/dev/null || true
systemctl start openvpn-server@server 2>/dev/null || true

echo
echo "Host EasyRSA is ready."
echo "  easyrsa: ${EASYRSA_DIR}/easyrsa"
echo "  CA:      ${PKI_DIR}/ca.crt"
echo
echo "Now rebuild openvpn-node:"
echo "  cd <openvpn-node>/core && docker compose up --build -d"
echo "  curl http://127.0.0.1:8090/node/health"
