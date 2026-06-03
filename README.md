# OpenVPN Node

Server-side data-plane service deployed on each VPN server. Generates OpenVPN certificates and `.ovpn` profiles for **user-manager**.

Uses the same layout as `user-manager/core` (`backend/src/vpn_node_core`, domain-driven API, `AppContainer`, YAML config).

## API (HMAC-signed except health)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/node/health` | Node health |
| `POST` | `/node/vpn/openvpn/create` | Create client cert + return `.ovpn` |
| `POST` | `/node/vpn/openvpn/delete` | Revoke client |

Headers for signed routes:

```
X-Node-Timestamp: <unix_seconds>
X-Node-Signature: HMAC-SHA256(secret, timestamp + METHOD + path + body)
```

## Quick start (mock PKI, local dev)

```bash
cd openvpn-node/core
cp .env.example .env
pip install -e ".[dev]"
OPENVPN_NODE_ENVIRONMENT=config PYTHONPATH=backend/src python -m vpn_node_core
```

API: http://localhost:8090/docs

## Docker

```bash
docker compose up --build
```

Health: http://localhost:8090/node/health

## Register in user-manager

When creating a server in user-manager, set:

```json
{
  "connection": { "host": "<server-ip>", "api_port": 8090 },
  "openvpn": {
    "enabled": true,
    "node_api_secret": "change-me-node-secret",
    "vpn_host": "vpn.example.com"
  }
}
```

Then provision via `POST /api/v1/openvpn/provision`.

## Production on a real OpenVPN host

Set `MOCK_MODE=false` and mount host paths:

- `/etc/openvpn/easy-rsa`
- `/etc/openvpn/ccd`

The service runs EasyRSA and reloads OpenVPN via `systemctl`.

## Tests

```bash
PYTHONPATH=backend/src pytest backend/tests -v
```
