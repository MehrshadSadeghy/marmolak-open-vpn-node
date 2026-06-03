import logging
from typing import TYPE_CHECKING

import uvicorn
from fastapi import APIRouter, FastAPI

from vpn_node_core.config import APIConfig
from vpn_node_core.core.manager.base import Manager

if TYPE_CHECKING:
    from vpn_node_core.container import AppContainer

LOGGER = logging.getLogger(__name__)


class APIManager(Manager):
    def __init__(
        self,
        api_config: APIConfig,
        container: "AppContainer",
        routers: list[APIRouter],
    ) -> None:
        self._config = api_config
        self._container = container
        self._routers = routers
        self._app: FastAPI | None = None
        self._uvicorn_server: uvicorn.Server | None = None

    async def setup(self) -> None:
        LOGGER.info("Setting up API Manager")
        self._app = FastAPI(
            debug=self._config.debug,
            title=self._config.title,
            version=self._config.version,
        )
        for router in self._routers:
            self._app.include_router(router)
        self._app.state.container = self._container

    async def run(self) -> None:
        if self._app is None:
            raise ValueError("APIManager is not setup")
        LOGGER.info("Running API on %s:%s", self._config.host, self._config.port)
        self._uvicorn_server = uvicorn.Server(
            config=uvicorn.Config(
                app=self._app,
                host=self._config.host,
                port=self._config.port,
            )
        )
        await self._uvicorn_server.serve()

    async def teardown(self) -> None:
        LOGGER.info("Tearing down API Manager")
