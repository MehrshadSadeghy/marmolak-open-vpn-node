#!/usr/bin/env bash
# Apply OpenVPN server tuning for Iranian ISPs (Irancell / MCI / ADSL).
# Run on the VPN server as root.

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="/etc/openvpn/server"
PKI="/etc/openvpn/easy-rsa/pki"

log() { echo "==> $*"; }

write_udp_variant() {
  local name="$1"
  local port="$2"
  local subnet="$3"
  local pool_file="$4"
  local status_file="$5"
  local log_file="$6"

  cat > "${SERVER_DIR}/${name}.conf" <<EOF
# OpenVPN — Iran ISP optimized (${name})
port ${port}
proto udp
dev tun

ca ${PKI}/ca.crt
cert ${PKI}/issued/server.crt
key ${PKI}/private/server.key
dh ${PKI}/dh.pem

topology subnet
server ${subnet}
ifconfig-pool-persist ${pool_file}

data-ciphers AES-256-GCM:AES-128-GCM
tls-version-min 1.2
verify-client-cert require
remote-cert-tls client

tun-mtu 1400
mssfix 1360
sndbuf 0
rcvbuf 0
fast-io

keepalive 10 120
persist-key
persist-tun

user nobody
group nogroup

status ${status_file}
log-append ${log_file}
verb 3
explicit-exit-notify 1

push "redirect-gateway def1 bypass-dhcp"
push "tun-mtu 1400"
push "mssfix 1360"
push "dhcp-option DNS 1.1.1.1"
push "dhcp-option DNS 8.8.8.8"
push "dhcp-option DNS 149.112.112.112"
EOF
}

write_tcp_variant() {
  local name="$1"
  local port="$2"
  local subnet="$3"
  local pool_file="$4"
  local status_file="$5"
  local log_file="$6"

  cat > "${SERVER_DIR}/${name}.conf" <<EOF
# OpenVPN — Iran ISP optimized (${name})
port ${port}
proto tcp
dev tun

ca ${PKI}/ca.crt
cert ${PKI}/issued/server.crt
key ${PKI}/private/server.key
dh ${PKI}/dh.pem

topology subnet
server ${subnet}
ifconfig-pool-persist ${pool_file}

data-ciphers AES-256-GCM:AES-128-GCM
tls-version-min 1.2
verify-client-cert require
remote-cert-tls client

tun-mtu 1400
mssfix 1360
sndbuf 0
rcvbuf 0
fast-io
tcp-nodelay

keepalive 10 120
persist-key
persist-tun

user nobody
group nogroup

status ${status_file}
log-append ${log_file}
verb 3

push "redirect-gateway def1 bypass-dhcp"
push "tun-mtu 1400"
push "mssfix 1360"
push "dhcp-option DNS 1.1.1.1"
push "dhcp-option DNS 8.8.8.8"
push "dhcp-option DNS 149.112.112.112"
EOF
}

log "Writing optimized server configs..."
install -m 0644 "${SCRIPT_DIR}/iran-optimized-server.conf" "${SERVER_DIR}/server.conf"
write_udp_variant "udp-1194" 1194 "10.8.0.0 255.255.255.0" \
  "/var/log/openvpn/ipp-udp-1194.txt" \
  "/var/log/openvpn/openvpn-status-udp-1194.log" \
  "/var/log/openvpn/openvpn-udp-1194.log"
write_udp_variant "udp-443" 443 "10.10.0.0 255.255.255.0" \
  "/var/log/openvpn/ipp-udp-443.txt" \
  "/var/log/openvpn/openvpn-status-udp-443.log" \
  "/var/log/openvpn/openvpn-udp-443.log"
write_tcp_variant "tcp-443" 443 "10.9.0.0 255.255.255.0" \
  "/var/log/openvpn/ipp-tcp-443.txt" \
  "/var/log/openvpn/openvpn-status-tcp-443.log" \
  "/var/log/openvpn/openvpn-tcp-443.log"

log "Kernel network tuning..."
cat > /etc/sysctl.d/99-openvpn-iran.conf <<'EOF'
# Throughput and buffer sizes for VPN clients (Iran mobile paths)
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
EOF
sysctl --system >/dev/null 2>&1 || sysctl -p /etc/sysctl.d/99-openvpn-iran.conf

log "Firewall — ensure OpenVPN ports are open..."
for rule in 1194/udp 443/tcp 443/udp; do
  ufw allow "${rule}" >/dev/null 2>&1 || true
done
ufw reload >/dev/null 2>&1 || true

enable_instance() {
  local instance="$1"
  systemctl enable "openvpn-server@${instance}" >/dev/null 2>&1 || true
  systemctl restart "openvpn-server@${instance}"
}

log "Starting OpenVPN instances (UDP 1194, TCP 443, UDP 443)..."
enable_instance "server"
enable_instance "tcp-443"
enable_instance "udp-443"

log "Listening sockets:"
ss -ulnp | grep -E '1194|443' || true
ss -tlnp | grep ':443' || true

log "Done. Users should re-download .ovpn files from the bot."
