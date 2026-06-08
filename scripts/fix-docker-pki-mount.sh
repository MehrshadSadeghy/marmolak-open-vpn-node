#!/usr/bin/env bash
# Fix openvpn-node PKI bind mount when the container sees an empty /etc/openvpn/easy-rsa/pki.
#
# Run from the openvpn-node project directory on the VPN server:
#   sudo ./scripts/fix-docker-pki-mount.sh
#
# Common causes:
#   - /etc/openvpn/easy-rsa/pki is a symlink (Docker mounts it as empty)
#   - Docker previously created an empty mount point over the real PKI

set -euo pipefail

PKI_DIR="/etc/openvpn/easy-rsa/pki"
ENV_FILE=".env"

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
    "$(readlink -f "${PKI_DIR}" 2>/dev/null || true)" \
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

log "Stopping openvpn-node (unmounts PKI path on host)..."
docker compose down

real_pki="$(find_real_pki || true)"
if [[ -z "${real_pki}" || ! -f "${real_pki}/ca.crt" ]]; then
  echo "No PKI with ca.crt found. Run: sudo ./scripts/fix-easyrsa-host.sh" >&2
  exit 1
fi
real_pki="$(readlink -f "${real_pki}")"
log "Real PKI directory: ${real_pki}"

if [[ -L "${PKI_DIR}" ]] || [[ "$(readlink -f "${PKI_DIR}" 2>/dev/null || echo "")" != "${real_pki}" ]]; then
  log "Installing PKI at ${PKI_DIR} as a real directory..."
  if [[ -e "${PKI_DIR}" || -L "${PKI_DIR}" ]]; then
    backup="${PKI_DIR}.bak.$(date +%s)"
    mv "${PKI_DIR}" "${backup}"
    log "Backed up old path to ${backup}"
  fi
  mkdir -p "${PKI_DIR}"
  cp -a "${real_pki}/." "${PKI_DIR}/"
fi

if [[ ! -f "${PKI_DIR}/ca.crt" ]]; then
  echo "PKI still missing at ${PKI_DIR}/ca.crt" >&2
  exit 1
fi

log "Host PKI contents:"
ls -la "${PKI_DIR}/" | head -10

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

set_env_var "OPENVPN_PKI_HOST_PATH" "${PKI_DIR}"
set_env_var "OPENVPN_PKI_DIR" "/mnt/openvpn-pki"
log "Updated ${ENV_FILE}: OPENVPN_PKI_HOST_PATH=${PKI_DIR}, OPENVPN_PKI_DIR=/mnt/openvpn-pki"

log "Starting openvpn-node..."
docker compose up -d

sleep 2
pki_in_container="/mnt/openvpn-pki"
if grep -q '^OPENVPN_PKI_DIR=' "${ENV_FILE}" 2>/dev/null; then
  pki_in_container="$(grep '^OPENVPN_PKI_DIR=' "${ENV_FILE}" | cut -d= -f2-)"
fi

if docker compose exec -T openvpn-node test -f "${pki_in_container}/ca.crt"; then
  echo
  echo "SUCCESS: container sees ${pki_in_container}/ca.crt"
  curl -s http://127.0.0.1:8090/node/health || true
  echo
else
  echo
  echo "Container still missing ca.crt at ${pki_in_container}. Run: sudo ./scripts/diagnose-pki.sh" >&2
  exit 1
fi
