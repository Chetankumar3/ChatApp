"""
CM-side registry of live Main Service gRPC addresses.

- Bootstrapped from Redis on startup.
- Refreshed every `interval` seconds by `refresh_loop`.
- New addresses get a persistent gRPC channel **immediately** on refresh.
- Failed addresses are skipped by `get_stub()`; the failed mark is cleared
  on the next refresh cycle (the server may have recovered).
- A single `MainRouterStub` per channel is used for `RouteInboundMessage`
  to forward WebSocket payloads to the Main Service.
"""

import asyncio

import grpc
from .grpc_proto import grpc_stub_pb2_grpc as pb2_grpc

from .redis.registry import get_service_addresses


class MainServiceDirectory:

    def __init__(self):
        self._addresses: list[str] = []
        self._failed:    set[str]  = set()
        # Both channels and stubs are kept alive forever once created.
        self._channels: dict[str, grpc.aio.Channel]           = {}
        self._stubs:    dict[str, pb2_grpc.MainRouterStub]     = {}

    # ── Internal channel/stub management ─────────────────────────────────────

    def _ensure_channel(self, address: str) -> None:
        """Create a persistent channel + stub for *address* if not yet present."""
        if address not in self._channels:
            self._channels[address] = grpc.aio.insecure_channel(address)
            self._stubs[address]    = pb2_grpc.MainRouterStub(self._channels[address])

    # ── Public API ────────────────────────────────────────────────────────────

    async def refresh(self) -> None:
        """
        Pull the current list of Main Service addresses from Redis.
        Eagerly creates channels for any newly discovered addresses.
        """
        addresses = await get_service_addresses("main")
        # Remove stale failure marks for addresses no longer registered
        self._failed = {f for f in self._failed if f in addresses}
        self._addresses = addresses
        # Eagerly connect to every address we haven't seen before
        for addr in addresses:
            self._ensure_channel(addr)

    def mark_failed(self, address: str) -> None:
        """
        Temporarily mark *address* as unhealthy so `get_stub` skips it.
        The mark is cleared on the next `refresh` call.
        """
        self._failed.add(address)

    def get_stub(self) -> tuple[str, pb2_grpc.MainRouterStub] | None:
        """
        Return ``(address, stub)`` for the first non-failed Main Service, or
        ``None`` if no healthy server is currently known.

        The returned stub exposes:
          • ``stub.RouteInboundMessage(pb2.InboundMessage(...))``
        """
        for addr in self._addresses:
            if addr not in self._failed:
                return addr, self._stubs[addr]
        return None

    async def refresh_loop(self, interval: int = 10) -> None:
        """Background coroutine: keep the directory fresh."""
        while True:
            await asyncio.sleep(interval)
            try:
                await self.refresh()
            except Exception as exc:
                print(f"[cm_directory] Refresh failed: {exc}")


# Module-level singleton — imported by both websocket_endpoint and the CM
# gRPC servicer.  Initialised (first refresh) inside the FastAPI lifespan.
directory = MainServiceDirectory()
