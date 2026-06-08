from typing import Annotated

from fastapi import Depends, Request

from vpn_node_core.openvpn_domain.service.openvpn_manager_service import OpenVpnManagerService
from vpn_node_core.openvpn_domain.service.server_endpoint_service import ServerEndpointService


def get_openvpn_manager(request: Request) -> OpenVpnManagerService:
    return request.app.state.container.get_openvpn_manager_service()


def get_server_endpoint_service(request: Request) -> ServerEndpointService:
    return request.app.state.container.get_server_endpoint_service()


OpenVpnManagerDep = Annotated[OpenVpnManagerService, Depends(get_openvpn_manager)]
ServerEndpointDep = Annotated[ServerEndpointService, Depends(get_server_endpoint_service)]
