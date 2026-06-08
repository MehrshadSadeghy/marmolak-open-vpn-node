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
if [[ -L "${PKI_DIR}" ]]; then
  echo "[WARN] PKI path is a symlink -> $(readlink -f "${PKI_DIR}")"
  echo "       Docker bind mounts often see an EMPTY dir when the source is a symlink."
  echo "       Set OPENVPN_PKI_HOST_PATH to the resolved path in .env"
fi
if mountpoint -q "${PKI_DIR}" 2>/dev/null; then
  echo "[WARN] PKI path is an active mount point (often Docker). Host ls may differ from disk."
  findmnt -T "${PKI_DIR}" 2>/dev/null || true
fi
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
echo "PKI path type on host:"
stat -c '  %F  %n' "${PKI_DIR}" 2>/dev/null || stat "${PKI_DIR}"
echo "Resolved PKI path: $(readlink -f "${PKI_DIR}" 2>/dev/null || echo unknown)"
echo "Host listing (no symlink follow):"
ls -la "${EASYRSA_DIR}/" 2>/dev/null || true
echo "Host PKI contents:"
ls -la "${PKI_DIR}/" 2>/dev/null || true

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
echo "Inside openvpn-node container (if running):"
if docker compose ps --status running 2>/dev/null | grep -q openvpn-node; then
  docker compose exec -T openvpn-node ls -la /etc/openvpn/easy-rsa/pki/ 2>/dev/null || \
    docker compose exec -T openvpn-node ls -la /etc/openvpn/easy-rsa/pki/
  docker compose exec -T openvpn-node test -f /etc/openvpn/easy-rsa/pki/ca.crt && \
    echo "[OK]   container sees ca.crt" || \
    echo "[MISS] container does NOT see ca.crt (Docker volume mount problem)"
else
  echo "  openvpn-node container is not running in this directory"
fi

echo
echo "docker-compose volumes:"
docker compose config 2>/dev/null | awk '/volumes:/{flag=1;next}/^[[:space:]]*[a-zA-Z]/{if(flag) exit}flag' || true

echo
resolved_pki="$(readlink -f "${PKI_DIR}" 2>/dev/null || true)"
if [[ -n "${resolved_pki}" && "${resolved_pki}" != "${PKI_DIR}" ]]; then
  echo "Recommended .env (symlink-safe mount):"
  echo "  OPENVPN_PKI_HOST_PATH=${resolved_pki}"
fi

echo
echo "Fix commands:"
echo "  sudo ./scripts/fix-docker-pki-mount.sh"
echo "  sudo ./scripts/fix-easyrsa-host.sh"
