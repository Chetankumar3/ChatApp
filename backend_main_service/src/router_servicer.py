"""
Main Service gRPC servicer.

Implements one RPC on behalf of the Main Service:

  MainRouter.RouteInboundMessage
    - Persists the message to PostgreSQL.
    - Fans out to online recipients via a 2-pass delivery strategy:
        Pass 1  - query Redis, group users by CM address, send in parallel.
        Sleep   - await asyncio.sleep(0.075) to let reconnecting clients finish
                  their new TCP handshake before we re-query Redis.
        Pass 2  - re-query Redis for users whose delivery failed, send again.
                  Failures on the second pass are silently dropped + lazily evicted.

CM workers verify JWTs locally (shared JWT_SECRET) — no Main Service round-trip.
"""

import asyncio
from datetime import datetime

import grpc
from sqlalchemy import select

from .grpc_proto import grpc_stub_pb2 as pb2
from .grpc_proto import grpc_stub_pb2_grpc as pb2_grpc
from .. import DB_models
from ..database import AsyncSessionLocal
from redis_service.registry import get_user_route, delete_user_route

# ── Persistent gRPC channels & stubs to CM workers ───────────────────────────
# Keyed by "host:port".  Created lazily on first contact, never closed.
_cm_channels: dict[str, grpc.aio.Channel] = {}
_cm_stubs:    dict[str, pb2_grpc.ConnectionManagerStub] = {}


def _get_cm_stub(address: str) -> pb2_grpc.ConnectionManagerStub:
    """Return (or create) a persistent ConnectionManagerStub for *address*."""
    if address not in _cm_stubs:
        if address not in _cm_channels:
            _cm_channels[address] = grpc.aio.insecure_channel(address)
        _cm_stubs[address] = pb2_grpc.ConnectionManagerStub(_cm_channels[address])
    return _cm_stubs[address]


# ── Low-level single-attempt delivery helper ─────────────────────────────────

async def _try_deliver(
    cm_address: str,
    outbound: pb2.OutboundMessage,
) -> list[int]:
    """
    Attempt to deliver *outbound* to *cm_address* exactly once.

    Returns the list of user IDs that were NOT delivered (either returned by
    the CM in DeliveryAck.failed_user_ids, or all target IDs on a transport
    error).  Does NOT perform lazy eviction — callers decide that.
    """
    stub = _get_cm_stub(cm_address)
    try:
        ack: pb2.DeliveryAck = await stub.DeliverOutboundMessage(outbound, timeout=5)
        return list(ack.failed_user_ids)
    except Exception as exc:
        print(f"[Main] gRPC transport error to CM {cm_address}: {exc}")
        return list(outbound.target_user_ids)


# ── 2-pass fan-out ────────────────────────────────────────────────────────────

async def _fanout(
    user_ids:   list[int],
    sender_id:  int,
    outbound_factory,          # callable(target_user_ids) → pb2.OutboundMessage
) -> None:
    """
    Deliver to *user_ids* (excluding *sender_id*) with a 2-pass retry.

    Pass 1 - route every online user to their CM, send in parallel.
    Sleep  - 75 ms to allow reconnecting clients to finish handshake.
    Pass 2 - re-route only the failed IDs; remaining failures are lazily
             evicted and silently dropped.
    """
    # ── Pass 1: collect routes ────────────────────────────────────────────────
    cm_to_users: dict[str, list[int]] = {}
    for uid in user_ids:
        if uid == sender_id:
            continue          # sender already has the message client-side
        addr = await get_user_route(uid)
        if addr:
            cm_to_users.setdefault(addr, []).append(uid)

    if not cm_to_users:
        return

    # ── Pass 1: send in parallel ──────────────────────────────────────────────
    tasks = []
    addr_to_users: dict[str, list[int]] = {}
    for addr, uids in cm_to_users.items():
        msg = outbound_factory(uids)
        tasks.append(_try_deliver(addr, msg))
        addr_to_users[addr] = uids

    results = await asyncio.gather(*tasks)

    # Collect all IDs that failed in pass 1
    failed_pass1: list[int] = []
    for addr, result_failed in zip(cm_to_users.keys(), results):
        failed_pass1.extend(result_failed)
        # Evict only IDs that the CM explicitly reported as missing
        # (those it couldn't find in its own active_websockets).
        # Transport failures are handled in pass 2.

    if not failed_pass1:
        return

    # ── Sleep: let reconnecting clients finish their new TCP handshake ────────
    await asyncio.sleep(0.075)

    # ── Pass 2: re-route failed IDs ───────────────────────────────────────────
    cm_to_users_retry: dict[str, list[int]] = {}
    for uid in failed_pass1:
        addr = await get_user_route(uid)
        if addr:
            cm_to_users_retry.setdefault(addr, []).append(uid)

    if not cm_to_users_retry:
        # Nobody reconnected — evict stale routes
        for uid in failed_pass1:
            await delete_user_route(uid)
        return

    retry_tasks = []
    for addr, uids in cm_to_users_retry.items():
        msg = outbound_factory(uids)
        retry_tasks.append(_try_deliver(addr, msg))

    retry_results = await asyncio.gather(*retry_tasks)

    # Pass 2 failures → silent drop + lazy evict
    for addr, result_failed in zip(cm_to_users_retry.keys(), retry_results):
        for uid in result_failed:
            await delete_user_route(uid)

    # Also evict any IDs that never got a new route
    routed_in_retry = {uid for uids in cm_to_users_retry.values() for uid in uids}
    for uid in failed_pass1:
        if uid not in routed_in_retry:
            await delete_user_route(uid)


# ── Servicer ──────────────────────────────────────────────────────────────────

class MainRouterServicer(pb2_grpc.MainRouterServicer):

    # ── RouteInboundMessage ───────────────────────────────────────────────────

    async def RouteInboundMessage(
        self,
        request: pb2.InboundMessage,
        context: grpc.aio.ServicerContext,
    ) -> pb2.RoutingAck:
        async with AsyncSessionLocal() as db:
            try:
                if request.type == "direct_message":
                    return await self._handle_direct(request, db)
                elif request.type == "group_message":
                    return await self._handle_group(request, db)
                else:
                    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                    return pb2.RoutingAck(success=False, error="Unknown message type")
            except Exception as exc:
                context.set_code(grpc.StatusCode.INTERNAL)
                return pb2.RoutingAck(success=False, error=str(exc))

    # ── Direct message ────────────────────────────────────────────────────────

    async def _handle_direct(
        self,
        request: pb2.InboundMessage,
        db,
    ) -> pb2.RoutingAck:
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

        msg_id = db_msg.id

        def outbound_factory(uids: list[int]) -> pb2.OutboundMessage:
            return pb2.OutboundMessage(
                target_user_ids=uids,
                fromId=request.fromId,
                toId=request.toId,
                type=request.type,
                body=request.body,
                sentAt=request.sentAt,
                message_id=msg_id,
            )

        # Fire-and-forget fan-out (don't block the ACK to the sender's CM)
        asyncio.create_task(
            _fanout([request.toId], sender_id=request.fromId, outbound_factory=outbound_factory)
        )

        return pb2.RoutingAck(success=True, message_id=msg_id)

    # ── Group message ─────────────────────────────────────────────────────────

    async def _handle_group(
        self,
        request: pb2.InboundMessage,
        db,
    ) -> pb2.RoutingAck:
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
        group_user_ids: list[int] = list(
            await db.scalars(
                select(DB_models.mapTable.userId).where(
                    DB_models.mapTable.groupId == request.toId
                )
            )
        )

        # Write receipts — sender's marked received immediately
        receipts = []
        for uid in group_user_ids:
            receipt = DB_models.messageReceipt(
                groupMessageId=db_msg.id,
                userId=uid,
            )
            if uid == request.fromId:
                receipt.receivedAt = sent_at
            receipts.append(receipt)
        db.add_all(receipts)
        await db.commit()

        msg_id = db_msg.id

        def outbound_factory(uids: list[int]) -> pb2.OutboundMessage:
            return pb2.OutboundMessage(
                target_user_ids=uids,
                fromId=request.fromId,
                toId=request.toId,
                type=request.type,
                body=request.body,
                sentAt=request.sentAt,
                message_id=msg_id,
            )

        asyncio.create_task(
            _fanout(group_user_ids, sender_id=request.fromId, outbound_factory=outbound_factory)
        )

        return pb2.RoutingAck(success=True, message_id=msg_id)