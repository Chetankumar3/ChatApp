"""
CM-side gRPC servicer: receives outbound delivery requests from Main Service.

DeliveryAck.failed_user_ids:
  - Empty  → all target users received their message.
  - Non-empty → those user IDs were not found in this CM's active_websockets
    (they disconnected between the Main Service's Redis lookup and this call).
    Main Service will retry after a brief sleep.
"""

import json

import grpc

from .grpc_proto import grpc_stub_pb2 as pb2
from .grpc_proto import grpc_stub_pb2_grpc as pb2_grpc
from .state import get_connection


class ConnectionManagerServicer(pb2_grpc.ConnectionManagerServicer):

    async def DeliverOutboundMessage(
        self,
        request: pb2.OutboundMessage,
        context: grpc.aio.ServicerContext,
    ) -> pb2.DeliveryAck:

        payload = json.dumps({
            "type":       request.type,
            "fromId":     request.fromId,
            "toId":       request.toId,
            "body":       request.body,
            "sentAt":     request.sentAt,
            "message_id": request.message_id,
        })

        failed: list[int] = []

        for uid in request.target_user_ids:
            entry = get_connection(uid)

            if entry is None:
                # User is not connected to this CM instance.
                # Caller should re-query Redis and retry.
                failed.append(uid)
                continue

            ws, lock = entry
            async with lock:
                try:
                    await ws.send_text(payload)
                except Exception as exc:
                    print(f"[CM] WebSocket send failed for user {uid}: {exc}")
                    failed.append(uid)

        return pb2.DeliveryAck(failed_user_ids=failed)
