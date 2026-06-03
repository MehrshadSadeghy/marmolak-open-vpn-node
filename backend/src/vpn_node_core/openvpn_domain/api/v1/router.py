from fastapi import APIRouter, Depends, Request

from vpn_node_core.openvpn_domain.api.v1.dependency import OpenVpnManagerDep
from vpn_node_core.openvpn_domain.api.v1.dto import (
    CreateOpenVpnRequestDTO,
    CreateOpenVpnResponseDTO,
    DeleteOpenVpnRequestDTO,
    DeleteOpenVpnResponseDTO,
    HealthResponseDTO,
)
from vpn_node_core.openvpn_domain.auth.node_signature import verify_node_signature_factory

router = APIRouter(prefix="/node", tags=["openvpn-node"])


async def verify_signed_request(request: Request) -> None:
    container = request.app.state.container
    verifier = verify_node_signature_factory(container.get_config().openvpn)
    await verifier(request)


@router.get("/health", response_model=HealthResponseDTO)
async def health(service: OpenVpnManagerDep) -> HealthResponseDTO:
    status = await service.health()
    return HealthResponseDTO.from_status(status)


@router.post(
    "/vpn/openvpn/create",
    response_model=CreateOpenVpnResponseDTO,
    dependencies=[Depends(verify_signed_request)],
)
async def create_openvpn_user(
    body: CreateOpenVpnRequestDTO,
    service: OpenVpnManagerDep,
) -> CreateOpenVpnResponseDTO:
    result = await service.create_user(body.to_command())
    return CreateOpenVpnResponseDTO.from_result(result)


@router.post(
    "/vpn/openvpn/delete",
    response_model=DeleteOpenVpnResponseDTO,
    dependencies=[Depends(verify_signed_request)],
)
async def delete_openvpn_user(
    body: DeleteOpenVpnRequestDTO,
    service: OpenVpnManagerDep,
) -> DeleteOpenVpnResponseDTO:
    result = await service.delete_user(body.to_command())
    return DeleteOpenVpnResponseDTO.from_result(result)
