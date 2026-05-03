import asyncio
import os

import grpc
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .src import general, group, login, user
from .src.router_servicer import MainRouterServicer
from .database import engine
from . import DB_models

from .src.grpc_proto import grpc_stub_pb2_grpc as pb2_grpc
from .src.redis.registry import register_service, heartbeat_loop, deregister_service
from .src.redis.client import close_redis

SERVICE_GRPC_PORT       = int(os.getenv("SERVICE_GRPC_PORT",       "50050"))
SERVICE_HTTP_PORT       = int(os.getenv("SERVICE_HTTP_PORT",        "8000"))
SERVICE_ADVERTISE_HOST  = os.getenv("SERVICE_ADVERTISE_HOST",       "127.0.0.1")

_service_id: str | None = None


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(DB_models.Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _service_id
    print("Booting Main Service: ensuring database tables exist...")
    await init_db()

    advertise_addr = f"{SERVICE_ADVERTISE_HOST}:{SERVICE_GRPC_PORT}"
    _service_id = await register_service("main", advertise_addr)
    print(f"Registered Main Service in Redis as {advertise_addr} (id={_service_id})")

    heartbeat_task = asyncio.create_task(heartbeat_loop("main", _service_id))

    yield

    heartbeat_task.cancel()
    if _service_id:
        await deregister_service("main", _service_id)
    await close_redis()
    print("Main Service shut down gracefully.")


app = FastAPI(lifespan=lifespan, root_path="/ping/main_service")

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://16.112.64.12",
    "http://16.112.64.12.nip.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login.router,   tags=["Login"])
app.include_router(user.router,    prefix="/users",  tags=["User APIs"])
app.include_router(general.router,                   tags=["General APIs"])
app.include_router(group.router,   prefix="/groups", tags=["Group APIs"])


async def serve_fastapi():
    config = uvicorn.Config(app, host="0.0.0.0", port=SERVICE_HTTP_PORT)
    server = uvicorn.Server(config)
    await server.serve()


async def serve_grpc():
    server = grpc.aio.server()
    pb2_grpc.add_MainRouterServicer_to_server(MainRouterServicer(), server)
    listen_addr = f"[::]:{SERVICE_GRPC_PORT}"
    server.add_insecure_port(listen_addr)
    print(f"gRPC server listening on {listen_addr}")
    await server.start()
    await server.wait_for_termination()


async def main():
    print(f"Booting Main Service: FastAPI ({SERVICE_HTTP_PORT}) & gRPC ({SERVICE_GRPC_PORT})...")
    await asyncio.gather(serve_fastapi(), serve_grpc())


if __name__ == "__main__":
    asyncio.run(main())