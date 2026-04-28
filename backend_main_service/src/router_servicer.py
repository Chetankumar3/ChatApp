import asyncio
from datetime import datetime

import grpc
from sqlalchemy import select

import grpc_stub_pb2 as pb2
import grpc_stub_pb2_grpc as pb2_grpc
from .. import DB_models
from ..database import AsyncSessionLocal
from redis_service.registry import get_user_route, delete_user_route

# Long-lived gRPC channels to CM workers, keyed by "host:port"
_cm_channels: dict[str, grpc.aio.Channel] = {}


def _get_cm_stub(address: str) -> pb2_grpc.ConnectionManagerStub:
    if address not in _cm_channels:
        _cm_channels[address] = grpc.aio.insecure_channel(address)
    return pb2_grpc.ConnectionManagerStub(_cm_channels[address])


async def _deliver_to_cm(
    cm_address: str,
    outbound: pb2.OutboundMessage,
    target_user_ids: list[int],
):
    """Send OutboundMessage to a CM with 3 retries + exponential backoff.
    On total failure, lazy-evict all target users from Redis."""
    stub = _get_cm_stub(cm_address)
    for attempt in range(3):
        try:
            await stub.DeliverOutboundMessage(outbound, timeout=5)
            return
        except Exception:
            if attempt < 2:
                await asyncio.sleep(0.5 * (2 ** attempt))  # 0.5s → 1s

    # All 3 attempts failed — lazy evict so stale routes don't pile up
    for uid in target_user_ids:
        await delete_user_route(uid)


class MainRouterServicer(pb2_grpc.MainRouterServicer):

    async def RouteInboundMessage(self, request: pb2.InboundMessage, context):
        async with AsyncSessionLocal() as db:
            try:
                if request.type == "direct_message":
                    return await self._handle_direct(request, db)
                elif request.type == "group_message":
                    return await self._handle_group(request, db)
                else:
                    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                    return pb2.RoutingAck(success=False, error="Unknown message type")
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                return pb2.RoutingAck(success=False, error=str(e))

    async def _handle_direct(self, request: pb2.InboundMessage, db) -> pb2.RoutingAck:
        sent_at = datetime.fromisoformat(request.sentAt.replace("Z", "+00:00"))
        db_msg = DB_models.message(
            fromId=request.fromId,
            toId=request.toId,
            body=request.body,
            sentAt=sent_at,
        )
        db.add(db_msg)
        await db.flush()
        await db.refresh(db_msg)
        await db.commit()

        cm_address = await get_user_route(request.toId)
        if cm_address:
            outbound = pb2.OutboundMessage(
                target_user_ids=[request.toId],
                fromId=request.fromId,
                toId=request.toId,
                type=request.type,
                body=request.body,
                sentAt=request.sentAt,
                message_id=db_msg.id,
            )
            asyncio.create_task(_deliver_to_cm(cm_address, outbound, [request.toId]))

        return pb2.RoutingAck(success=True, message_id=db_msg.id)

    async def _handle_group(self, request: pb2.InboundMessage, db) -> pb2.RoutingAck:
        sent_at = datetime.fromisoformat(request.sentAt.replace("Z", "+00:00"))
        db_msg = DB_models.groupMessage(
            fromId=request.fromId,
            toId=request.toId,
            body=request.body,
            sentAt=sent_at,
        )
        db.add(db_msg)
        await db.flush()
        await db.refresh(db_msg)

        # Fetch all group members
        group_users = (await db.scalars(
            select(DB_models.mapTable.userId).where(DB_models.mapTable.groupId == request.toId)
        )).all()

        # Create receipts — sender's marked received immediately
        receipts = []
        for uid in group_users:
            receipt = DB_models.messageReceipt(groupMessageId=db_msg.id, userId=uid)
            if uid == request.fromId:
                receipt.receivedAt = sent_at
            receipts.append(receipt)
        db.add_all(receipts)
        await db.commit()

        # Fan out to online recipients, batched by CM address
        cm_to_users: dict[str, list[int]] = {}
        for uid in group_users:
            if uid == request.fromId:
                continue  # sender already has the message client-side
            cm_addr = await get_user_route(uid)
            if cm_addr:
                cm_to_users.setdefault(cm_addr, []).append(uid)

        for cm_addr, user_ids in cm_to_users.items():
            outbound = pb2.OutboundMessage(
                target_user_ids=user_ids,
                fromId=request.fromId,
                toId=request.toId,
                type=request.type,
                body=request.body,
                sentAt=request.sentAt,
                message_id=db_msg.id,
            )
            asyncio.create_task(_deliver_to_cm(cm_addr, outbound, user_ids))

        return pb2.RoutingAck(success=True, message_id=db_msg.id)
