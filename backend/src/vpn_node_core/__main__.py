import asyncio
import logging

from vpn_node_core.container import AppContainer

LOGGER = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    container = AppContainer()
    managers = container.get_managers()

    try:
        await asyncio.gather(*[manager.setup() for manager in managers])
        await asyncio.gather(*[manager.run() for manager in managers])
    except Exception:
        LOGGER.exception("openvpn-node failed")
        raise
    finally:
        await asyncio.gather(*[manager.teardown() for manager in managers])


if __name__ == "__main__":
    asyncio.run(main())
