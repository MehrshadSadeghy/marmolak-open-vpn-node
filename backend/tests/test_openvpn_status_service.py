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


def test_parse_openvpn_status_log_openvpn_26_csv_format():
    content = """TITLE,OpenVPN 2.6.20 x86_64-pc-linux-gnu [SSL (OpenSSL)] [LZO] [LZ4] [EPOLL] [PKCS11] [MH/PKTINFO] [AEAD] [DCO]
TIME,2026-06-10 12:48:00,1781095680
HEADER,CLIENT_LIST,Common Name,Real Address,Virtual Address,Virtual IPv6 Address,Bytes Received,Bytes Sent,Connected Since,Connected Since (time_t),Username,Client ID,Peer ID,Data Channel Cipher
CLIENT_LIST,9149049423,5.250.110.244:39303,10.8.0.5,,303825,982868,2026-06-10 12:42:17,1781095337,UNDEF,8,0,AES-256-GCM
HEADER,ROUTING_TABLE,Virtual Address,Common Name,Real Address,Last Ref,Last Ref (time_t)
ROUTING_TABLE,10.8.0.5,9149049423,5.250.110.244:39303,2026-06-10 12:47:59,1781095679
"""
    readings = parse_openvpn_status_log(content)
    assert len(readings) == 1
    assert readings[0].common_name == "9149049423"
    assert readings[0].bytes_received == 303825
    assert readings[0].bytes_sent == 982868
    assert readings[0].bytes_total == 1286693
