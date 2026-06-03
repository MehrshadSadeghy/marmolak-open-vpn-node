from typing import Annotated

from fastapi import Depends, Request

from vpn_node_core.openvpn_domain.service.openvpn_manager_service import OpenVpnManagerService


def get_openvpn_manager(request: Request) -> OpenVpnManagerService:
    return request.app.state.container.get_openvpn_manager_service()


OpenVpnManagerDep = Annotated[OpenVpnManagerService, Depends(get_openvpn_manager)]
