import asyncio
import logging
import os

import grpc
import uvicorn
import logging
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .src import general, group, login, user
from .src.router_servicer import MainRouterServicer
from .database import engine
from . import DB_models

from .src.grpc_proto import grpc_stub_pb2_grpc as pb2_grpc
from .src.redis.registry import register_service, heartbeat_loop, deregister_service
from .src.redis.client import close_redis
from starlette.exceptions import HTTPException as StarletteHTTPException

SERVICE_GRPC_PORT       = int(os.getenv("SERVICE_GRPC_PORT",       "50050"))
SERVICE_HTTP_PORT       = int(os.getenv("SERVICE_HTTP_PORT",        "8000"))
SERVICE_ADVERTISE_HOST  = os.getenv("SERVICE_ADVERTISE_HOST",       "127.0.0.1")

_service_id: str | None = None
error_logger = logging.getLogger("fastapi_errors")
error_logger.setLevel(logging.ERROR)
file_handler = RotatingFileHandler(
    filename="http_exceptions.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5, 
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - Path: %(url)s - Detail: %(message)s")
)
error_logger.addHandler(file_handler)


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
    "http://35.208.50.148",
    "http://35.208.50.148.nip.io",
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

# 1. Intercept explicitly raised HTTPExceptions (Both 4xx and 5xx)
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code < 500:
        # 4xx Client Fault: Log as warning, no traceback, return exact detail to client
        error_logger.warning(
            f"Client Error {exc.status_code}: {exc.detail}", 
            extra={"url": str(request.url)}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    else:
        # 5xx Server Fault explicitly raised: Log as error, include traceback, mask detail
        error_logger.error(
            f"Server Error {exc.status_code}: {exc.detail}", 
            extra={"url": str(request.url)},
            exc_info=True
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": "Internal Server Error"},
        )

# 2. Intercept unhandled native exceptions (Always 500)
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # 5xx Unhandled Server Fault: Log as critical error, include traceback, mask detail
    error_logger.error(
        f"Unhandled Server Error: {str(exc)}", 
        extra={"url": str(request.url)},
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

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