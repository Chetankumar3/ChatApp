import uuid
import asyncio
from .client import get_redis

SERVICE_TTL = 35  # seconds

async def register_service(service_type: str, advertise_address: str) -> str:
    """Register this instance and return the unique service_id."""
    r = await get_redis()
    service_id = str(uuid.uuid4())
    await r.set(f"service:{service_type}:{service_id}", advertise_address, ex=SERVICE_TTL)
    return service_id


async def heartbeat(service_type: str, service_id: str):
    r = await get_redis()
    await r.expire(f"service:{service_type}:{service_id}", SERVICE_TTL)


async def deregister_service(service_type: str, service_id: str):
    r = await get_redis()
    await r.delete(f"service:{service_type}:{service_id}")


async def get_user_route(user_id: int) -> str | None:
    r = await get_redis()
    return await r.get(f"user:{user_id}")


async def delete_user_route(user_id: int):
    r = await get_redis()
    await r.delete(f"user:{user_id}")


async def heartbeat_loop(service_type: str, service_id: str, interval: int = 10):
    """Background coroutine: renew service registration every `interval` seconds."""
    while True:
        await asyncio.sleep(interval)
        try:
            await heartbeat(service_type, service_id)
        except Exception as e:
            print(f"[heartbeat] Failed for {service_type}:{service_id}: {e}")
