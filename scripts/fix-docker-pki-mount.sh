#!/usr/bin/env bash
# Fix openvpn-node PKI visibility inside Docker.
#
# Docker on some hosts cannot read /etc/openvpn/easy-rsa/pki (userns, 0700 perms, mount quirks).
# This copies the system PKI into ./host-pki and points docker-compose at it.
#
# Run from the openvpn-node project directory on the VPN server:
#   sudo ./scripts/fix-docker-pki-mount.sh

set -euo pipefail

SYSTEM_PKI="/etc/openvpn/easy-rsa/pki"
LOCAL_PKI="host-pki"
ENV_FILE=".env"
PROJECT_DIR="$(pwd)"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

if [[ ! -f docker-compose.yml ]]; then
  echo "Run this from the openvpn-node project directory (where docker-compose.yml lives)." >&2
  exit 1
fi

log() {
  echo "==> $*"
}

find_real_pki() {
  local path
  for path in \
    "$(readlink -f "${SYSTEM_PKI}" 2>/dev/null || true)" \
    /etc/openvpn/easy-rsa/pki \
    /etc/openvpn/server/easy-rsa/pki \
    /etc/openvpn/server/pki; do
    if [[ -n "${path}" && -f "${path}/ca.crt" && -f "${path}/private/ca.key" ]]; then
      echo "${path}"
      return 0
    fi
  done
  find /etc/openvpn /root -path '*/pki/ca.crt' 2>/dev/null | head -1 | sed 's#/ca.crt##'
}

set_env_var() {
  local key="$1"
  local value="$2"
  if [[ -f "${ENV_FILE}" ]]; then
    if grep -q "^${key}=" "${ENV_FILE}"; then
      sed -i "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
    else
      echo "${key}=${value}" >> "${ENV_FILE}"
    fi
  else
    echo "${key}=${value}" > "${ENV_FILE}"
  fi
}

log "Stopping openvpn-node..."
docker compose down

real_pki="$(find_real_pki || true)"
if [[ -z "${real_pki}" || ! -f "${real_pki}/ca.crt" ]]; then
  echo "No PKI with ca.crt found. Run: sudo ./scripts/fix-easyrsa-host.sh" >&2
  exit 1
fi
real_pki="$(readlink -f "${real_pki}")"
log "System PKI: ${real_pki}"

log "Copying PKI into ${PROJECT_DIR}/${LOCAL_PKI} ..."
rm -rf "${LOCAL_PKI}"
mkdir -p "${LOCAL_PKI}"
cp -a "${real_pki}/." "${LOCAL_PKI}/"

chmod 755 "${LOCAL_PKI}"
chmod 755 "${LOCAL_PKI}/issued" "${LOCAL_PKI}/reqs" 2>/dev/null || true
chmod 777 "${LOCAL_PKI}/issued" "${LOCAL_PKI}/reqs" "${LOCAL_PKI}/private" 2>/dev/null || true
chmod 644 "${LOCAL_PKI}/ca.crt" "${LOCAL_PKI}/dh.pem" 2>/dev/null || true
chmod 600 "${LOCAL_PKI}/private/"* 2>/dev/null || true

if [[ ! -f "${LOCAL_PKI}/ca.crt" ]]; then
  echo "Copy failed: ${LOCAL_PKI}/ca.crt missing" >&2
  exit 1
fi

log "Local PKI ready:"
ls -la "${LOCAL_PKI}/" | head -10

# Use absolute path so Docker never mis-resolves a relative mount source.
local_pki_abs="${PROJECT_DIR}/${LOCAL_PKI}"
set_env_var "OPENVPN_PKI_HOST_PATH" "${local_pki_abs}"
set_env_var "OPENVPN_PKI_DIR" "/mnt/openvpn-pki"
log "Updated ${ENV_FILE}:"
log "  OPENVPN_PKI_HOST_PATH=${local_pki_abs}"
log "  OPENVPN_PKI_DIR=/mnt/openvpn-pki"

log "Starting openvpn-node..."
docker compose up -d --build

sleep 3
if docker compose exec -T openvpn-node test -f /mnt/openvpn-pki/ca.crt; then
  echo
  echo "SUCCESS: container sees /mnt/openvpn-pki/ca.crt"
  curl -s http://127.0.0.1:8090/node/health || true
  echo
  echo
  echo "New client certs are written to ${local_pki_abs}"
  echo "Keep this directory backed up (contains CA private key)."
else
  echo
  echo "FAILED: container still cannot read /mnt/openvpn-pki/ca.crt"
  echo "Run:"
  echo "  docker compose config | grep -A3 openvpn-pki"
  echo "  docker compose exec openvpn-node ls -la /mnt/openvpn-pki/"
  exit 1
fi
