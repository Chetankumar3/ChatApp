from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, or_, case
from sqlalchemy.orm import Session

from .. import DB_models, models
from ..database import get_db
from .login import get_current_user

router = APIRouter()


@router.get("/get_all_conversations/{userId}")
async def get_all_conversations(
    userId: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        messages = await db.scalars(
            select(DB_models.message)
            .where(or_(DB_models.message.fromId == userId, DB_models.message.toId == userId))
            .order_by(
                case(
                    (DB_models.message.toId == userId, DB_models.message.fromId),
                    else_=DB_models.message.toId,
                ),
                DB_models.message.sentAt,
            )
        )
        messages = messages.all()

        formatted_direct_messages: dict = {}
        for msg in messages:
            other = msg.toId if msg.fromId == userId else msg.fromId
            formatted_direct_messages.setdefault(other, []).append(msg)

        associated_users = await db.scalars(
            select(DB_models.user).where(DB_models.user.id.in_(formatted_direct_messages.keys()))
        )
        associated_users = associated_users.all()

        group_ids = await db.scalars(
            select(DB_models.mapTable.groupId).where(DB_models.mapTable.userId == userId)
        )
        group_ids = group_ids.all()

        associated_groups = await db.scalars(
            select(DB_models.group).where(DB_models.group.id.in_(group_ids))
        )
        associated_groups = associated_groups.all()

        group_messages = await db.scalars(
            select(DB_models.groupMessage)
            .where(DB_models.groupMessage.toId.in_(group_ids))
            .order_by(DB_models.groupMessage.toId, DB_models.groupMessage.sentAt)
        )
        group_messages = group_messages.all()

        formatted_group_messages: dict = defaultdict(list)
        for msg in group_messages:
            formatted_group_messages[msg.toId].append(msg)

        from_user_gm_ids = {m.id for m in group_messages if m.fromId == userId}
        message_receipts = await db.scalars(
            select(DB_models.messageReceipt).where(
                DB_models.messageReceipt.groupMessageId.in_(from_user_gm_ids)
            )
        )
        receipts_by_id = {mr.groupMessageId: mr for mr in message_receipts.all()}

        for msgs in formatted_group_messages.values():
            for m in msgs:
                if m.id in receipts_by_id:
                    m.receipts = receipts_by_id[m.id]

        return {
            "direct_messages": messages,
            "group_messages": formatted_group_messages,
            "associated_users": associated_users,
            "associated_groups": associated_groups,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_user_info/{userId}", response_model=models.user)
async def get_user_info(
    userId: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_info = await db.execute(select(DB_models.user).where(DB_models.user.id == userId))
        user_info = user_info.scalar_one_or_none()
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        return user_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/change_username/{userId}")
async def change_username(
    userId: int,
    data: models.UsernameUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        await db.execute(
            update(DB_models.user).where(DB_models.user.id == userId).values(username=data.newUsername)
        )
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
