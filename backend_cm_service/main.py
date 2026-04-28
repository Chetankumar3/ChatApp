import asyncio
import grpc
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ChatApp.backend_cm_service.src import websocket_endpoint
# TODO: Import your generated gRPC classes and Servicer implementation
# from .grpc_layer import connection_manager_pb2_grpc
# from .grpc_layer.servicer import ConnectionManagerServicer

app = FastAPI(root_path="/chatapp/cm_service")

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

app.include_router(websocket_endpoint.router)


async def serve_fastapi():
    # Run Uvicorn programmatically
    config = uvicorn.Config(app, host="0.0.0.0", port=8001) # Dynamic port for Worker N
    server = uvicorn.Server(config)
    await server.serve()

async def serve_grpc():
    server = grpc.aio.server()
    # TODO: Register your servicer
    # connection_manager_pb2_grpc.add_ConnectionManagerServicer_to_server(ConnectionManagerServicer(), server)
    
    server.add_insecure_port('[::]:50051') # Dynamic port for Worker N
    await server.start()
    await server.wait_for_termination()

async def main():
    print("Booting Connection Manager: FastAPI (8001) & gRPC (50051)...")
    await asyncio.gather(
        serve_fastapi(),
        serve_grpc()
    )

if __name__ == "__main__":
    asyncio.run(main())