from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClientTrafficReading:
    common_name: str
    bytes_received: int
    bytes_sent: int

    @property
    def bytes_total(self) -> int:
        return self.bytes_received + self.bytes_sent


def _append_reading(
    readings: list[ClientTrafficReading],
    *,
    common_name: str,
    bytes_received: int,
    bytes_sent: int,
) -> None:
    if not common_name or common_name in {"Common Name", "UNDEF"}:
        return
    readings.append(
        ClientTrafficReading(
            common_name=common_name,
            bytes_received=bytes_received,
            bytes_sent=bytes_sent,
        )
    )


def parse_openvpn_status_log(content: str) -> list[ClientTrafficReading]:
    readings: list[ClientTrafficReading] = []
    in_legacy_client_list = False

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("OpenVPN CLIENT LIST"):
            in_legacy_client_list = True
            continue
        if in_legacy_client_list and line.startswith("ROUTING TABLE"):
            break

        parts = [part.strip() for part in line.split(",")]

        # OpenVPN 2.6+ machine-readable status format.
        if parts[0] == "CLIENT_LIST" and len(parts) >= 7:
            try:
                _append_reading(
                    readings,
                    common_name=parts[1],
                    bytes_received=int(parts[5]),
                    bytes_sent=int(parts[6]),
                )
            except ValueError:
                pass
            continue

        if not in_legacy_client_list:
            continue
        if line.startswith("Updated,") or line.startswith("Common Name,"):
            continue
        if len(parts) < 4:
            continue

        try:
            _append_reading(
                readings,
                common_name=parts[0],
                bytes_received=int(parts[2]),
                bytes_sent=int(parts[3]),
            )
        except ValueError:
            continue

    return readings


def read_client_traffic(status_log_path: str) -> list[ClientTrafficReading]:
    path = Path(status_log_path)
    if not path.is_file():
        return []
    content = path.read_text(encoding="utf-8", errors="replace")
    return parse_openvpn_status_log(content)
