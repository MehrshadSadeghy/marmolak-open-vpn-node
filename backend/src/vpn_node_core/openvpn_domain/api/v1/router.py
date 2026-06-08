import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from vpn_node_core.openvpn_domain.api.v1.dependency import OpenVpnManagerDep, ServerEndpointDep
from vpn_node_core.openvpn_domain.api.v1.dto import (
    ApplyEndpointRequestDTO,
    ApplyEndpointResponseDTO,
    CreateOpenVpnRequestDTO,
    CreateOpenVpnResponseDTO,
    DeleteOpenVpnRequestDTO,
    DeleteOpenVpnResponseDTO,
    HealthResponseDTO,
)
from vpn_node_core.openvpn_domain.auth.node_signature import verify_node_signature_factory

router = APIRouter(prefix="/node", tags=["openvpn-node"])
LOGGER = logging.getLogger(__name__)


async def verify_signed_request(request: Request) -> None:
    container = request.app.state.container
    verifier = verify_node_signature_factory(container.get_config().openvpn)
    await verifier(request)


@router.get("/health", response_model=HealthResponseDTO)
async def health(request: Request, service: OpenVpnManagerDep) -> HealthResponseDTO:
    status = await service.health()
    config = request.app.state.container.get_config().openvpn
    return HealthResponseDTO.from_status(
        status,
        server_port=config.server_port,
        server_proto=config.server_proto,
    )


@router.post(
    "/vpn/openvpn/create",
    response_model=CreateOpenVpnResponseDTO,
    dependencies=[Depends(verify_signed_request)],
)
async def create_openvpn_user(
    body: CreateOpenVpnRequestDTO,
    service: OpenVpnManagerDep,
) -> CreateOpenVpnResponseDTO:
    try:
        result = await service.create_user(body.to_command())
    except RuntimeError as exc:
        LOGGER.exception("OpenVPN create failed for %s", body.common_name)
        raise HTTPException(
            status_code=503,
            detail=(
                "OpenVPN certificate creation failed. "
                "Set MOCK_MODE=true for testing or configure EasyRSA on the host."
            ),
        ) from exc
    return CreateOpenVpnResponseDTO.from_result(result)


@router.post(
    "/vpn/openvpn/apply-endpoint",
    response_model=ApplyEndpointResponseDTO,
    dependencies=[Depends(verify_signed_request)],
)
async def apply_openvpn_endpoint(
    body: ApplyEndpointRequestDTO,
    service: ServerEndpointDep,
) -> ApplyEndpointResponseDTO:
    proto = body.proto.lower()
    if proto not in ("udp", "tcp"):
        raise HTTPException(status_code=400, detail="proto must be udp or tcp")
    try:
        result = await service.apply_endpoint(body.port, proto)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        LOGGER.exception("OpenVPN endpoint apply failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ApplyEndpointResponseDTO.from_result(result)


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
