#!/usr/bin/env bash
# Print PKI / OpenVPN diagnostics for openvpn-node troubleshooting.

set -euo pipefail

EASYRSA_DIR="/etc/openvpn/easy-rsa"
PKI_DIR="${EASYRSA_DIR}/pki"
SERVER_CONF="/etc/openvpn/server/server.conf"

echo "=== OpenVPN PKI diagnostics ==="
echo

check_path() {
  local label="$1"
  local path="$2"
  if [[ -e "${path}" ]]; then
    echo "[OK]   ${label}: ${path}"
  else
    echo "[MISS] ${label}: ${path}"
  fi
}

check_path "easyrsa script" "${EASYRSA_DIR}/easyrsa"
check_path "bundled easyrsa" "/usr/share/easy-rsa/easyrsa"
check_path "PKI directory" "${PKI_DIR}"
check_path "CA certificate" "${PKI_DIR}/ca.crt"
check_path "CA private key" "${PKI_DIR}/private/ca.key"
check_path "issued dir" "${PKI_DIR}/issued"
check_path "private dir" "${PKI_DIR}/private"
check_path "server.conf" "${SERVER_CONF}"
check_path "status log" "/var/log/openvpn/openvpn-status.log"

if [[ -f "${SERVER_CONF}" ]]; then
  echo
  echo "server.conf certificate paths:"
  awk '/^(ca|cert|key|dh) / {print "  " $0}' "${SERVER_CONF}" || true
fi

echo
echo "Searching for ca.crt on host..."
find /etc/openvpn /root -name 'ca.crt' 2>/dev/null | head -20 || true

echo
echo "OpenVPN service:"
systemctl is-active openvpn-server@server 2>/dev/null || echo "  not active"

echo
echo "Node health (if running locally):"
curl -s http://127.0.0.1:8090/node/health 2>/dev/null || echo "  node API not reachable on :8090"

echo
echo "Fix command:"
echo "  sudo ./scripts/fix-easyrsa-host.sh"
