from dataclasses import dataclass


@dataclass
class ClientCertificate:
    common_name: str
    ca_cert: str
    client_cert: str
    client_key: str
