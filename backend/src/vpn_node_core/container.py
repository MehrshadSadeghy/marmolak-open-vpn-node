import os
from functools import lru_cache

from vpn_node_core.config import Config, load_config
from vpn_node_core.core.manager.api_manager import APIManager
from vpn_node_core.core.manager.base import Manager
from vpn_node_core.openvpn_domain.api.v1 import router as openvpn_router
from vpn_node_core.openvpn_domain.service.easyrsa_service import EasyRsaService
from vpn_node_core.openvpn_domain.service.openvpn_manager_service import OpenVpnManagerService

singleton = lru_cache


class AppContainer:
    @singleton
    def get_config(self) -> Config:
        environment = os.environ.get("OPENVPN_NODE_ENVIRONMENT", "config")
        return load_config(environment)

    @singleton
    def get_easyrsa_service(self) -> EasyRsaService:
        return EasyRsaService(self.get_config().openvpn)

    @singleton
    def get_openvpn_manager_service(self) -> OpenVpnManagerService:
        return OpenVpnManagerService(
            self.get_config().openvpn,
            easyrsa=self.get_easyrsa_service(),
        )

    @singleton
    def get_api_manager(self) -> APIManager:
        return APIManager(
            api_config=self.get_config().api,
            container=self,
            routers=[openvpn_router.router],
        )

    @singleton
    def get_managers(self) -> list[Manager]:
        return [self.get_api_manager()]
