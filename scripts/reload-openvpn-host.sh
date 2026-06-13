#!/usr/bin/env bash
set -euo pipefail

PKI_CRL="${OPENVPN_PKI_DIR:-/etc/openvpn/easy-rsa/pki}/crl.pem"
LEGACY_CRL="/etc/openvpn/crl.pem"
SERVICE="${OPENVPN_SERVICE_NAME:-openvpn-server@server}"

if [[ -f "$PKI_CRL" ]]; then
  cp "$PKI_CRL" "$LEGACY_CRL"
  chmod 644 "$LEGACY_CRL"
fi

systemctl restart "$SERVICE"
