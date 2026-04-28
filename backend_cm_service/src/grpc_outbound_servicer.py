import json

import grpc

import grpc_stub_pb2 as pb2
import grpc_stub_pb2_grpc as pb2_grpc
from .state import get_connection


class ConnectionManagerServicer(pb2_grpc.ConnectionManagerServicer):

    async def DeliverOutboundMessage(
        self, request: pb2.OutboundMessage, context: grpc.aio.ServicerContext
    ) -> pb2.DeliveryAck:
        payload = json.dumps({
            "type": request.type,
            "fromId": request.fromId,
            "toId": request.toId,
            "body": request.body,
            "sentAt": request.sentAt,
            "message_id": request.message_id,
        })

        failed: list[int] = []

        for uid in request.target_user_ids:
            entry = get_connection(uid)
            if entry is None:
                continue  # user disconnected between route lookup and delivery

            ws, lock = entry
            async with lock:
                try:
                    await ws.send_text(payload)
                except Exception as e:
                    failed.append(uid)
                    print(f"[CM] WebSocket send failed for user {uid}: {e}")

        if failed:
            return pb2.DeliveryAck(
                success=False,
                error=f"Failed to deliver to user ids: {failed}",
            )
        return pb2.DeliveryAck(success=True)
