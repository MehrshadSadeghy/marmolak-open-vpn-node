#!/usr/bin/env bash
# Bind the real OpenVPN server.conf into this project so Docker can mount it.
#
# Run once on the VPN server (as root):
#   sudo ./scripts/setup-server-conf-bind.sh
#
# After reboot, run again or add the mount line to /etc/fstab.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET="${PROJECT_DIR}/server.conf"
SOURCE="/etc/openvpn/server/server.conf"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

if [[ ! -f "${SOURCE}" ]]; then
  echo "OpenVPN config not found: ${SOURCE}" >&2
  exit 1
fi

if mountpoint -q "${TARGET}" 2>/dev/null; then
  echo "Already bind-mounted: ${TARGET}"
  exit 0
fi

touch "${TARGET}"
mount --bind "${SOURCE}" "${TARGET}"
echo "Bind-mounted ${SOURCE} -> ${TARGET}"
echo "Now run: docker compose up --build -d"
