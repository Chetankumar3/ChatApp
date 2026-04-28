import asyncio
import grpc
import chat_pb2_grpc
from serve_cm import ChatServiceServicer

async def serve():
    # Initialize the async gRPC server
    server = grpc.aio.server()
    
    # Attach your specific implementation to the server
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatServiceServicer(), server)
    
    # Bind to a port (50051 is standard for gRPC)
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    print(f"Starting gRPC server on {listen_addr}")
    
    # Start and keep the process alive
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())