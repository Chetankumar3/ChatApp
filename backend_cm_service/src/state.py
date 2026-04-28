import asyncio
from fastapi import WebSocket

# Shared in-process RAM store: user_id → (WebSocket, per-user asyncio.Lock)
# The per-user Lock prevents concurrent writes to the same WebSocket.
active_websockets: dict[int, tuple[WebSocket, asyncio.Lock]] = {}

# Protects structural mutations to the dict itself (add/remove)
_dict_lock = asyncio.Lock()


async def add_connection(user_id: int, ws: WebSocket):
    async with _dict_lock:
        active_websockets[user_id] = (ws, asyncio.Lock())


async def remove_connection(user_id: int):
    async with _dict_lock:
        active_websockets.pop(user_id, None)


def get_connection(user_id: int) -> tuple[WebSocket, asyncio.Lock] | None:
    """Non-blocking lookup — safe because dict reads are atomic in CPython."""
    return active_websockets.get(user_id)
