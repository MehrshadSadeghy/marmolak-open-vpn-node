from vpn_node_core.openvpn_domain.service.openvpn_status_service import parse_openvpn_status_log


def test_parse_openvpn_status_log():
    content = """OpenVPN CLIENT LIST
Updated,Tue Jun  8 17:00:00 2026
Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
3250003542,1.2.3.4:54321,1048576,2097152,Tue Jun  8 16:00:00 2026
4978390220,5.6.7.8:12345,500,700,Tue Jun  8 16:30:00 2026

ROUTING TABLE
Updated,Tue Jun  8 17:00:00 2026
Virtual Address,Common Name,Real Address,Last Ref
10.8.0.2,3250003542,1.2.3.4:54321,Tue Jun  8 17:00:00 2026
"""
    readings = parse_openvpn_status_log(content)
    assert len(readings) == 2
    assert readings[0].common_name == "3250003542"
    assert readings[0].bytes_total == 1048576 + 2097152
    assert readings[1].common_name == "4978390220"
    assert readings[1].bytes_total == 1200
