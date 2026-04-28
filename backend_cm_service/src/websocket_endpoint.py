import json
import os

import grpc
import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import grpc_stub_pb2 as pb2
from .state import add_connection, remove_connection
from .cm_directory import directory

from redis_service.registry import set_user_route, delete_user_route

router = APIRouter()

THIS_CM_GRPC_HOST = os.getenv("SERVICE_ADVERTISE_HOST", "127.0.0.1")
THIS_CM_GRPC_PORT = os.getenv("SERVICE_GRPC_PORT", "50051")
MAIN_SERVICE_HTTP = os.getenv("MAIN_SERVICE_HTTP", "http://127.0.0.1:8000")


async def _validate_token(user_id: int, token: str) -> bool:
    """Ask Main Service to verify the JWT and confirm it belongs to user_id."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{MAIN_SERVICE_HTTP}/internal/validate-ws",
                json={"user_id": user_id, "token": token},
                timeout=5.0,
            )
        return resp.status_code == 200
    except Exception:
        return False


async def _forward_to_main(inbound: pb2.InboundMessage) -> pb2.RoutingAck:
    """Forward an inbound message to Main Service, cycling servers on failure."""
    last_exc: Exception | None = None
    for attempt in range(3):
        result = directory.get_stub()
        if result is None:
            raise RuntimeError("No Main Service available in directory")
        addr, stub = result
        try:
            return await stub.RouteInboundMessage(inbound, timeout=5)
        except grpc.aio.AioRpcError as e:
            directory.mark_failed(addr)
            last_exc = e
    raise last_exc or RuntimeError("All Main Service attempts failed")


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    # --- AUTH PHASE ---
    auth_header = websocket.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        await websocket.close(code=1008)
        return

    token = auth_header.split(" ", 1)[1]
    if not await _validate_token(user_id, token):
        await websocket.close(code=1008)
        return

    # --- REGISTRATION PHASE ---
    await websocket.accept()
    await add_connection(user_id, websocket)
    cm_grpc_address = f"{THIS_CM_GRPC_HOST}:{THIS_CM_GRPC_PORT}"
    await set_user_route(user_id, cm_grpc_address)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "detail": "Invalid JSON"}))
                continue

            inbound = pb2.InboundMessage(
                fromId=user_id,
                toId=int(msg["toId"]),
                type=msg["type"],
                body=msg["body"],
                sentAt=msg["sentAt"],
                client_uuid=msg.get("client_uuid", ""),
            )

            try:
                ack = await _forward_to_main(inbound)
                await websocket.send_text(json.dumps({
                    "type": "ack",
                    "client_uuid": msg.get("client_uuid"),
                    "message_id": ack.message_id,
                    "success": ack.success,
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({"type": "error", "detail": str(e)}))

    except WebSocketDisconnect:
        pass
    finally:
        await remove_connection(user_id)
        await delete_user_route(user_id)
