import asyncio
import logging
from logging.handlers import RotatingFileHandler
import grpc
from .grpc_proto import grpc_stub_pb2_grpc as pb2_grpc
from .redis.registry import get_service_addresses

# Configure standard logger
cm_logger = logging.getLogger("cm_directory_errors")
cm_logger.setLevel(logging.ERROR)
file_handler = RotatingFileHandler(
    filename="cm_directory_exceptions.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - gRPC: %(message)s")
)
cm_logger.addHandler(file_handler)

class MainServiceDirectory:

    def __init__(self):
        self._addresses: list[str] = []
        self._failed:    set[str]  = set()
        self._channels: dict[str, grpc.aio.Channel]           = {}
        self._stubs:    dict[str, pb2_grpc.MainRouterStub]     = {}

    def _ensure_channel(self, address: str) -> None:
        if address not in self._channels:
            self._channels[address] = grpc.aio.insecure_channel(address)
            self._stubs[address]    = pb2_grpc.MainRouterStub(self._channels[address])

    async def refresh(self) -> None:
        addresses = await get_service_addresses("main")
        self._failed = {f for f in self._failed if f in addresses}
        self._addresses = addresses
        for addr in addresses:
            self._ensure_channel(addr)

    def mark_failed(self, address: str) -> None:
        self._failed.add(address)

    def get_stub(self) -> tuple[str, pb2_grpc.MainRouterStub] | None:
        for addr in self._addresses:
            if addr not in self._failed:
                return addr, self._stubs[addr]
        return None

    async def refresh_loop(self, interval: int = 10) -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                await self.refresh()
            except Exception as exc:
                # Remove `print`. Use logger with exc_info=True to preserve Redis traceback
                cm_logger.error(f"Directory refresh failed: {str(exc)}", exc_info=True)


directory = MainServiceDirectory()