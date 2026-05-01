from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import Session

from .. import DB_models, models
from ..database import get_db
from .login import get_current_user

router = APIRouter()


@router.put("/create/{creator_id}", response_model=models.groupCreationOutput)
async def create_group(
    data: models.groupCreationInput,
    creator_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        new_group = DB_models.group(**data.model_dump(exclude_unset=True, exclude={"members"}))
        db.add(new_group)
        await db.flush()
        await db.refresh(new_group)

        members = list(dict.fromkeys((data.members or []) + [creator_id]))
        db.add_all([
            DB_models.mapTable(groupId=new_group.id, userId=uid, admin=(uid == creator_id))
            for uid in members
        ])
        await db.commit()
        return {"message": "Group created successfully", "groupId": new_group.id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_group_info/{group_id}", response_model=models.group)
async def get_group_info(
    group_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        group_info = await db.execute(select(DB_models.group).where(DB_models.group.id == group_id))
        group_info = group_info.scalar_one_or_none()
        if not group_info:
            raise HTTPException(status_code=404, detail="Group not found")

        members = await db.scalars(
            select(DB_models.user)
            .join(DB_models.mapTable, DB_models.user.id == DB_models.mapTable.userId)
            .where(DB_models.mapTable.groupId == group_id)
        )
        return {**group_info.__dict__, "members": members.all()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _require_admin(db, group_id: int, modifier_id: int):
    rel = await db.execute(
        select(DB_models.mapTable).where(
            and_(DB_models.mapTable.groupId == group_id, DB_models.mapTable.userId == modifier_id)
        )
    )
    rel = rel.scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail="No group found or user is not a member")
    if not rel.admin:
        raise HTTPException(status_code=403, detail="Only admins can perform this action")


@router.put("/update/{modifier_id}/{group_id}", response_model=models.APIResponse)
async def update_group(
    modifier_id: int,
    group_id: int,
    group: models.groupUpdationInput,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        await _require_admin(db, group_id, modifier_id)
        group_exists = await db.scalar(select(DB_models.group).where(DB_models.group.id == group_id))
        if not group_exists:
            raise HTTPException(status_code=404, detail="Group not found")
        await db.execute(
            update(DB_models.group).where(DB_models.group.id == group_id)
            .values(**group.model_dump(exclude_unset=True))
        )
        await db.commit()
        return {"success": True, "message": "Group updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_member/{modifier_id}/{group_id}", response_model=models.APIResponse)
async def add_member(
    group_id: int,
    modifier_id: int,
    user_ids: list[int],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        await _require_admin(db, group_id, modifier_id)
        if not await db.scalar(select(DB_models.group).where(DB_models.group.id == group_id)):
            raise HTTPException(status_code=404, detail="Group not found")

        existing = await db.scalars(select(DB_models.user.id).where(DB_models.user.id.in_(user_ids)))
        db.add_all([
            DB_models.mapTable(groupId=group_id, userId=uid) for uid in existing.all()
        ])
        await db.commit()
        return {"success": True, "message": "Member added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remove_member/{modifier_id}/{group_id}", response_model=models.APIResponse)
async def remove_member(
    group_id: int,
    modifier_id: int,
    user_ids: list[int],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        await _require_admin(db, group_id, modifier_id)
        if not await db.scalar(select(DB_models.group).where(DB_models.group.id == group_id)):
            raise HTTPException(status_code=404, detail="Group not found")
        await db.execute(
            delete(DB_models.mapTable).where(
                and_(DB_models.mapTable.groupId == group_id, DB_models.mapTable.userId.in_(user_ids))
            )
        )
        await db.commit()
        return {"success": True, "message": "Member removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/make_admin/{modifier_id}/{group_id}", response_model=models.APIResponse)
async def make_admin(
    group_id: int,
    modifier_id: int,
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        await _require_admin(db, group_id, modifier_id)
        if not await db.scalar(select(DB_models.group).where(DB_models.group.id == group_id)):
            raise HTTPException(status_code=404, detail="Group not found")
        await db.execute(
            update(DB_models.mapTable)
            .where(and_(DB_models.mapTable.groupId == group_id, DB_models.mapTable.userId == user_id))
            .values(admin=True)
        )
        await db.commit()
        return {"success": True, "message": "User promoted to admin successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/exit/{group_id}/{user_id}", response_model=models.APIResponse)
async def exit_group(
    group_id: int,
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if not await db.scalar(select(DB_models.group).where(DB_models.group.id == group_id)):
            raise HTTPException(status_code=404, detail="Group not found")
        entry = await db.scalar(
            select(DB_models.mapTable).where(
                and_(DB_models.mapTable.groupId == group_id, DB_models.mapTable.userId == user_id)
            )
        )
        if not entry:
            raise HTTPException(status_code=400, detail="User not in group")
        await db.delete(entry)
        await db.commit()
        return {"success": True, "message": "User exited group successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{modifier_id}/{group_id}", response_model=models.APIResponse)
async def delete_group(
    modifier_id: int,
    group_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if not await db.scalar(
            select(DB_models.mapTable).where(
                and_(
                    DB_models.mapTable.groupId == group_id,
                    DB_models.mapTable.userId == modifier_id,
                    DB_models.mapTable.admin == True,
                )
            )
        ):
            raise HTTPException(status_code=403, detail="Only admins can delete the group")

        db_group = await db.scalar(select(DB_models.group).where(DB_models.group.id == group_id))
        if not db_group:
            raise HTTPException(status_code=404, detail="Group not found")

        await db.execute(delete(DB_models.mapTable).where(DB_models.mapTable.groupId == group_id))
        await db.execute(
            delete(DB_models.messageReceipt).where(
                DB_models.messageReceipt.groupMessageId.in_(
                    select(DB_models.groupMessage.id).where(DB_models.groupMessage.toId == group_id)
                )
            )
        )
        await db.execute(delete(DB_models.groupMessage).where(DB_models.groupMessage.toId == group_id))
        await db.delete(db_group)
        await db.commit()
        return {"success": True, "message": "Group deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
