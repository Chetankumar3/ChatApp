"""
CM WebSocket endpoint.

Auth flow (JWT validated locally — no Main Service round-trip):
  1. Client opens  ws://cm-host:port/ws/{user_id}
     with header   Authorization: Bearer <jwt>
  2. CM verifies the JWT signature with the shared JWT_SECRET and confirms
     the token's user_id matches the path's user_id.
  3. On valid → accept WebSocket, register in RAM + Redis.
  4. On invalid → close(1008) immediately.

Message flow:
  User → WebSocket → CM → gRPC (RouteInboundMessage) → Main Service
  Main Service → gRPC (DeliverOutboundMessage) → CM → WebSocket → User
"""

import json
import os

import grpc
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .grpc_proto import grpc_stub_pb2 as pb2
from .state import add_connection, remove_connection
from .cm_directory import directory

from redis_service.registry import set_user_route, delete_user_route

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

router = APIRouter()

THIS_CM_GRPC_HOST = os.getenv("SERVICE_ADVERTISE_HOST", "127.0.0.1")
THIS_CM_GRPC_PORT = os.getenv("SERVICE_GRPC_PORT", "50051")


# ── Local JWT validation ─────────────────────────────────────────────────────

def _validate_token(user_id: int, token: str) -> bool:
    """
    Verify the JWT signature with the shared secret and confirm its
    `user_id` claim matches the user_id in the WebSocket path.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False

    token_user_id = payload.get("user_id")
    if token_user_id is None:
        return False
    return int(token_user_id) == int(user_id)


# ── gRPC helper ──────────────────────────────────────────────────────────────

async def _forward_to_main(inbound: pb2.InboundMessage) -> pb2.RoutingAck:
    """
    Forward an inbound WebSocket payload to Main Service over gRPC.
    Cycles through known servers on transport failure.
    """
    last_exc: Exception | None = None

    for _ in range(len(directory._addresses) or 1):
        result = directory.get_stub()
        if result is None:
            break
        addr, stub = result
        try:
            return await stub.RouteInboundMessage(inbound, timeout=5)
        except grpc.aio.AioRpcError as exc:
            directory.mark_failed(addr)
            last_exc = exc

    raise last_exc or RuntimeError("No Main Service available in directory")


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):

    # ── 1. Extract token ──────────────────────────────────────────────────────
    auth_header = websocket.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        await websocket.close(code=1008)
        return

    token = auth_header.split(" ", 1)[1]

    # ── 2. Validate JWT locally ───────────────────────────────────────────────
    if not _validate_token(user_id, token):
        await websocket.close(code=1008)
        return

    # ── 3. Accept & register ──────────────────────────────────────────────────
    await websocket.accept()
    await add_connection(user_id, websocket)

    cm_grpc_address = f"{THIS_CM_GRPC_HOST}:{THIS_CM_GRPC_PORT}"
    await set_user_route(user_id, cm_grpc_address)

    # ── 4. Message loop ───────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "detail": "Invalid JSON"})
                )
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
                    "type":        "ack",
                    "client_uuid": msg.get("client_uuid"),
                    "message_id":  ack.message_id,
                    "success":     ack.success,
                }))
            except Exception as exc:
                await websocket.send_text(
                    json.dumps({"type": "error", "detail": str(exc)})
                )

    except WebSocketDisconnect:
        pass

    # ── 5. Cleanup ────────────────────────────────────────────────────────────
    finally:
        await remove_connection(user_id)
        await delete_user_route(user_id)
