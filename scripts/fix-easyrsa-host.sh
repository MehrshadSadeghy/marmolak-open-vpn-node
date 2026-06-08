#!/usr/bin/env bash
# Fix missing EasyRSA / CA on the VPN host for openvpn-node.
#
# Run on the VPN server (as root):
#   sudo ./scripts/fix-easyrsa-host.sh
#
# Then:
#   docker compose up --build -d
#   curl http://127.0.0.1:8090/node/health

set -euo pipefail

EASYRSA_DIR="/etc/openvpn/easy-rsa"
PKI_DIR="${EASYRSA_DIR}/pki"
SOURCE_DIR="/usr/share/easy-rsa"
SERVER_CONF="/etc/openvpn/server/server.conf"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

log() {
  echo "==> $*"
}

find_ca_from_server_conf() {
  if [[ ! -f "${SERVER_CONF}" ]]; then
    return 1
  fi
  local ca_path
  ca_path="$(awk '/^ca / {print $2; exit}' "${SERVER_CONF}")"
  if [[ -n "${ca_path}" && -f "${ca_path}" ]]; then
    echo "${ca_path}"
    return 0
  fi
  return 1
}

find_existing_pki_dir() {
  local candidate ca_path

  if [[ -f "${PKI_DIR}/ca.crt" && -f "${PKI_DIR}/private/ca.key" ]]; then
    echo "${PKI_DIR}"
    return 0
  fi

  if ca_path="$(find_ca_from_server_conf)"; then
    if [[ "${ca_path}" == */pki/ca.crt ]]; then
      candidate="${ca_path%/ca.crt}"
      if [[ -f "${candidate}/private/ca.key" ]]; then
        echo "${candidate}"
        return 0
      fi
    fi
  fi

  for candidate in \
    /etc/openvpn/easy-rsa/pki \
    /etc/openvpn/server/easy-rsa/pki \
    /etc/openvpn/server/pki \
    /root/openvpn-ca/pki \
    /root/easy-rsa/pki; do
    if [[ -f "${candidate}/ca.crt" && -f "${candidate}/private/ca.key" ]]; then
      echo "${candidate}"
      return 0
    fi
  done

  return 1
}

log "Installing packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq easy-rsa openvpn openssl

if [[ ! -f "${SOURCE_DIR}/easyrsa" ]]; then
  echo "easyrsa not found at ${SOURCE_DIR}/easyrsa after install." >&2
  exit 1
fi

mkdir -p "${EASYRSA_DIR}"

if [[ ! -f "${EASYRSA_DIR}/easyrsa" ]]; then
  log "Installing EasyRSA tools into ${EASYRSA_DIR}..."
  cp -a "${SOURCE_DIR}/." "${EASYRSA_DIR}/"
  chmod +x "${EASYRSA_DIR}/easyrsa"
fi

if existing_pki="$(find_existing_pki_dir)"; then
  log "Found existing PKI at ${existing_pki}"
  if [[ "${existing_pki}" != "${PKI_DIR}" ]]; then
    mkdir -p "$(dirname "${PKI_DIR}")"
    if [[ -e "${PKI_DIR}" && ! -L "${PKI_DIR}" ]]; then
      backup="${PKI_DIR}.bak.$(date +%s)"
      log "Backing up empty/incomplete PKI dir to ${backup}"
      mv "${PKI_DIR}" "${backup}"
    fi
    ln -sfn "${existing_pki}" "${PKI_DIR}"
    log "Linked ${PKI_DIR} -> ${existing_pki}"
  fi
else
  log "No existing PKI found. Creating a new one at ${PKI_DIR}..."
  mkdir -p "${PKI_DIR}/issued" "${PKI_DIR}/private" "${PKI_DIR}/reqs"
  chmod 700 "${PKI_DIR}/private"
  cd "${EASYRSA_DIR}"
  ./easyrsa init-pki
  ./easyrsa --batch build-ca nopass
  log "WARNING: New CA created. If OpenVPN server already uses a different CA,"
  log "         update server.conf to use ${PKI_DIR}/ca.crt or restore the old PKI."
fi

mkdir -p "${PKI_DIR}/issued" "${PKI_DIR}/private" "${PKI_DIR}/reqs"
chmod 700 "${PKI_DIR}/private"

if [[ ! -f "${PKI_DIR}/ca.crt" ]]; then
  echo "CA still missing at ${PKI_DIR}/ca.crt" >&2
  echo "Run: sudo ./scripts/diagnose-pki.sh" >&2
  exit 1
fi

if [[ ! -f "${PKI_DIR}/private/ca.key" ]]; then
  echo "CA private key missing at ${PKI_DIR}/private/ca.key" >&2
  echo "Cannot issue client certificates without ca.key." >&2
  exit 1
fi

log "Starting OpenVPN..."
systemctl enable openvpn-server@server 2>/dev/null || true
systemctl restart openvpn-server@server 2>/dev/null || systemctl start openvpn-server@server 2>/dev/null || true

echo
echo "PKI ready:"
echo "  CA:      ${PKI_DIR}/ca.crt"
echo "  CA key:  ${PKI_DIR}/private/ca.key"
echo "  easyrsa: ${EASYRSA_DIR}/easyrsa"
echo
echo "Next:"
echo "  cd <openvpn-node>/core"
echo "  docker compose up --build -d"
echo "  curl http://127.0.0.1:8090/node/health"
