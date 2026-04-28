import asyncio

import grpc
import grpc_stub_pb2_grpc as pb2_grpc

from redis_service.registry import get_service_addresses


class MainServiceDirectory:
    """Maintains a live list of Main Service gRPC addresses.

    - Refreshes from Redis every `interval` seconds.
    - Marks individual addresses as transiently failed so callers can
      skip them and try the next available server.
    - Failed marks are cleared on the next refresh cycle.
    """

    def __init__(self):
        self._addresses: list[str] = []
        self._failed: set[str] = set()
        self._channels: dict[str, grpc.aio.Channel] = {}

    async def refresh(self):
        addresses = await get_service_addresses("main")
        self._addresses = addresses
        # Clear failures for addresses still present; they may have recovered
        self._failed = {f for f in self._failed if f in addresses}

    def mark_failed(self, address: str):
        self._failed.add(address)

    def get_stub(self) -> tuple[str, pb2_grpc.MainRouterStub] | None:
        """Return (address, stub) for the first non-failed server, or None."""
        for addr in self._addresses:
            if addr not in self._failed:
                if addr not in self._channels:
                    self._channels[addr] = grpc.aio.insecure_channel(addr)
                return addr, pb2_grpc.MainRouterStub(self._channels[addr])
        return None

    async def refresh_loop(self, interval: int = 30):
        while True:
            await asyncio.sleep(interval)
            try:
                await self.refresh()
            except Exception as e:
                print(f"[cm_directory] Refresh failed: {e}")


# Module-level singleton — both websocket_endpoint and grpc_servicer import this
directory = MainServiceDirectory()
