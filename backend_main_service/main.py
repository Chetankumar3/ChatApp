import asyncio
import grpc
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ChatApp.backend_main_service.src import general, group, login
from ChatApp.backend_main_service.database import engine
import ChatApp.backend_main_service.DB_models as DB_models
from ChatApp.backend_main_service.src import user

# TODO: Import your generated gRPC classes and Servicer implementation
# from .grpc_layer import main_router_pb2_grpc
# from .grpc_layer.servicer import MainRouterServicer

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(DB_models.Base.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Booting up: Ensuring database tables exist...")
    await init_db()
    yield
    print("Shutting down gracefully...")

app = FastAPI(lifespan=lifespan, root_path="/chatapp/main_service")

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

app.include_router(login.router, tags=["Login"])
app.include_router(user.router, prefix="/users", tags=["User APIs"])
app.include_router(general.router, tags=["General APIs"])
app.include_router(group.router, prefix="/groups", tags=["Group APIs"])


async def serve_fastapi():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()

async def serve_grpc():
    server = grpc.aio.server()
    # TODO: Register your servicer
    # main_router_pb2_grpc.add_MainRouterServicer_to_server(MainRouterServicer(), server)
    
    server.add_insecure_port('[::]:50050')
    await server.start()
    await server.wait_for_termination()

async def main():
    print("Booting Main Service: FastAPI (8000) & gRPC (50050)...")
    await asyncio.gather(
        serve_fastapi(),
        serve_grpc()
    )

if __name__ == "__main__":
    asyncio.run(main())