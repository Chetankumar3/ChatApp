"""
Integration tests for the ``/groups`` router.

All endpoints now declare ``Depends(get_current_user)`` → every test uses
``authorized_client``.  ``authorized_client`` is pre-authenticated as
``user_a`` (Alice), who is guaranteed to exist in the DB for every test.

Because ``user_a`` is always available as the authenticated caller, she is
used as the group admin in every scenario that requires one, avoiding the
need to seed a separate admin user.  A second user (Bob) is seeded inline
via ``db_session`` only when a test specifically needs a distinct member or
a non-admin actor.

The bare ``client`` fixture (no token) is used only in the 401-rejection
tests at the bottom of each class.

Endpoint coverage
-----------------
  PUT    /groups/create/{creator_id}
  GET    /groups/get_group_info/{group_id}
  PUT    /groups/update/{modifier_id}/{group_id}
  POST   /groups/add_member/{modifier_id}/{group_id}
  DELETE /groups/exit/{group_id}/{user_id}
  DELETE /groups/delete/{modifier_id}/{group_id}
"""
from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import DB_models


# ── inline seeding helpers ────────────────────────────────────────────────────

async def _make_user(
    db_session: AsyncSession,
    *,
    name: str,
    username: str,
) -> DB_models.user:
    u = DB_models.user(
        name=name,
        email=f"{username}@test.com",
        username=username,
        displayPictureUrl=f"http://example.com/{username}.png",
    )
    db_session.add(u)
    await db_session.flush()
    await db_session.refresh(u)
    return u


async def _make_group(
    db_session: AsyncSession,
    *,
    admin: DB_models.user,
    members: list[DB_models.user] | None = None,
    name: str = "Test Group",
    description: str = "A test group",
) -> DB_models.group:
    g = DB_models.group(name=name, description=description)
    db_session.add(g)
    await db_session.flush()
    await db_session.refresh(g)

    db_session.add(DB_models.mapTable(groupId=g.id, userId=admin.id, admin=True))
    for m in (members or []):
        db_session.add(DB_models.mapTable(groupId=g.id, userId=m.id, admin=False))

    await db_session.commit()
    await db_session.refresh(g)
    return g


# ── PUT /groups/create/{creator_id} ──────────────────────────────────────────

class TestCreateGroup:

    async def test_returns_200_with_group_id(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
    ) -> None:
        resp = await authorized_client.put(
            f"/groups/create/{user_a.id}",
            json={"name": "My Group", "description": "desc", "members": []},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "groupId" in body
        assert isinstance(body["groupId"], int)

    async def test_creator_is_recorded_as_admin(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
    ) -> None:
        create = await authorized_client.put(
            f"/groups/create/{user_a.id}",
            json={"name": "Admin Group", "description": "desc", "members": []},
        )
        assert create.status_code == 200
        gid = create.json()["groupId"]

        # An admin-only action by user_a must succeed
        update = await authorized_client.put(
            f"/groups/update/{user_a.id}/{gid}",
            json={"name": "Admin Group Renamed", "description": "desc"},
        )
        assert update.status_code == 200

    async def test_listed_members_are_added_to_group(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="cg_bob1")
        await db_session.commit()

        create = await authorized_client.put(
            f"/groups/create/{user_a.id}",
            json={"name": "Group With Bob", "description": "desc", "members": [bob.id]},
        )
        assert create.status_code == 200
        gid = create.json()["groupId"]

        info = await authorized_client.get(f"/groups/get_group_info/{gid}")
        assert info.status_code == 200
        member_ids = {m["id"] for m in info.json()["members"]}
        assert user_a.id in member_ids
        assert bob.id in member_ids

    async def test_missing_name_returns_422(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
    ) -> None:
        resp = await authorized_client.put(
            f"/groups/create/{user_a.id}",
            json={"description": "No name provided"},
        )

        assert resp.status_code == 422

    async def test_creator_counted_once_even_if_listed_in_members(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
    ) -> None:
        create = await authorized_client.put(
            f"/groups/create/{user_a.id}",
            json={"name": "Dedup", "description": "desc", "members": [user_a.id]},
        )
        assert create.status_code == 200
        gid = create.json()["groupId"]

        info = await authorized_client.get(f"/groups/get_group_info/{gid}")
        assert info.status_code == 200
        all_ids = [m["id"] for m in info.json()["members"]]
        assert all_ids.count(user_a.id) == 1

    async def test_unauthenticated_request_returns_401(
        self,
        client: AsyncClient,
        user_a: DB_models.user,
    ) -> None:
        resp = await client.put(
            f"/groups/create/{user_a.id}",
            json={"name": "G", "description": "d", "members": []},
        )

        assert resp.status_code == 401


# ── GET /groups/get_group_info/{group_id} ─────────────────────────────────────

class TestGetGroupInfo:

    async def test_returns_correct_name_and_description(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        group = await _make_group(
            db_session, admin=user_a, name="Alpha", description="Alpha desc",
        )

        resp = await authorized_client.get(f"/groups/get_group_info/{group.id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Alpha"
        assert body["description"] == "Alpha desc"

    async def test_members_list_contains_all_seeded_members(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="gi_bob1")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await authorized_client.get(f"/groups/get_group_info/{group.id}")

        assert resp.status_code == 200
        member_ids = {m["id"] for m in resp.json()["members"]}
        assert user_a.id in member_ids
        assert bob.id in member_ids

    async def test_nonexistent_group_id_returns_error(
        self,
        authorized_client: AsyncClient,
    ) -> None:
        resp = await authorized_client.get("/groups/get_group_info/999999")

        assert resp.status_code >= 400

    async def test_unauthenticated_request_returns_401(
        self,
        client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        group = await _make_group(db_session, admin=user_a)

        resp = await client.get(f"/groups/get_group_info/{group.id}")

        assert resp.status_code == 401


# ── PUT /groups/update/{modifier_id}/{group_id} ───────────────────────────────

class TestUpdateGroup:

    async def test_admin_can_rename_group(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        group = await _make_group(db_session, admin=user_a, name="Before")

        resp = await authorized_client.put(
            f"/groups/update/{user_a.id}/{group.id}",
            json={"name": "After", "description": "updated"},
        )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_rename_is_reflected_in_get_group_info(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        group = await _make_group(db_session, admin=user_a, name="Old Name")

        await authorized_client.put(
            f"/groups/update/{user_a.id}/{group.id}",
            json={"name": "New Name", "description": "desc"},
        )

        info = await authorized_client.get(f"/groups/get_group_info/{group.id}")
        assert info.status_code == 200
        assert info.json()["name"] == "New Name"

    async def test_non_admin_member_cannot_update_group(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="upd_bob1")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await authorized_client.put(
            f"/groups/update/{bob.id}/{group.id}",
            json={"name": "Hijacked", "description": "desc"},
        )

        assert resp.status_code >= 400

    async def test_user_not_in_group_cannot_update(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        outsider = await _make_user(db_session, name="Outsider", username="upd_out1")
        group = await _make_group(db_session, admin=user_a)

        resp = await authorized_client.put(
            f"/groups/update/{outsider.id}/{group.id}",
            json={"name": "Ghost Edit", "description": "desc"},
        )

        assert resp.status_code >= 400

    async def test_nonexistent_group_returns_error(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
    ) -> None:
        resp = await authorized_client.put(
            f"/groups/update/{user_a.id}/999999",
            json={"name": "Ghost", "description": "desc"},
        )

        assert resp.status_code >= 400

    async def test_unauthenticated_request_returns_401(
        self,
        client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        group = await _make_group(db_session, admin=user_a)

        resp = await client.put(
            f"/groups/update/{user_a.id}/{group.id}",
            json={"name": "Unauth Edit", "description": "desc"},
        )

        assert resp.status_code == 401


# ── POST /groups/add_member/{modifier_id}/{group_id} ─────────────────────────

class TestAddMember:

    async def test_admin_can_add_a_new_member(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="add_bob1")
        group = await _make_group(db_session, admin=user_a)

        resp = await authorized_client.post(
            f"/groups/add_member/{user_a.id}/{group.id}",
            json=[bob.id],
        )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_added_member_visible_in_group_info(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="add_bob2")
        group = await _make_group(db_session, admin=user_a)

        await authorized_client.post(
            f"/groups/add_member/{user_a.id}/{group.id}",
            json=[bob.id],
        )

        info = await authorized_client.get(f"/groups/get_group_info/{group.id}")
        assert info.status_code == 200
        member_ids = {m["id"] for m in info.json()["members"]}
        assert bob.id in member_ids

    async def test_non_admin_cannot_add_members(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob   = await _make_user(db_session, name="Bob",   username="add_bob3")
        carol = await _make_user(db_session, name="Carol", username="add_carol3")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await authorized_client.post(
            f"/groups/add_member/{bob.id}/{group.id}",
            json=[carol.id],
        )

        assert resp.status_code >= 400

    async def test_user_not_in_group_cannot_add_members(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        outsider = await _make_user(db_session, name="Outsider", username="add_out1")
        newbie   = await _make_user(db_session, name="Newbie",   username="add_new1")
        group    = await _make_group(db_session, admin=user_a)

        resp = await authorized_client.post(
            f"/groups/add_member/{outsider.id}/{group.id}",
            json=[newbie.id],
        )

        assert resp.status_code >= 400

    async def test_nonexistent_group_returns_error(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="add_bob4")
        await db_session.commit()

        resp = await authorized_client.post(
            f"/groups/add_member/{user_a.id}/999999",
            json=[bob.id],
        )

        assert resp.status_code >= 400

    async def test_unauthenticated_request_returns_401(
        self,
        client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob   = await _make_user(db_session, name="Bob", username="add_bob5")
        group = await _make_group(db_session, admin=user_a)

        resp = await client.post(
            f"/groups/add_member/{user_a.id}/{group.id}",
            json=[bob.id],
        )

        assert resp.status_code == 401


# ── DELETE /groups/exit/{group_id}/{user_id} ──────────────────────────────────

class TestExitGroup:

    async def test_member_can_exit_group(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="ex_bob1")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await authorized_client.delete(f"/groups/exit/{group.id}/{bob.id}")

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_exited_member_no_longer_in_group_info(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="ex_bob2")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        await authorized_client.delete(f"/groups/exit/{group.id}/{bob.id}")

        info = await authorized_client.get(f"/groups/get_group_info/{group.id}")
        assert info.status_code == 200
        member_ids = {m["id"] for m in info.json()["members"]}
        assert bob.id not in member_ids

    async def test_admin_can_exit_their_own_group(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        group = await _make_group(db_session, admin=user_a)

        resp = await authorized_client.delete(f"/groups/exit/{group.id}/{user_a.id}")

        assert resp.status_code == 200

    async def test_user_not_in_group_returns_error(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        outsider = await _make_user(db_session, name="Outsider", username="ex_out1")
        group    = await _make_group(db_session, admin=user_a)

        resp = await authorized_client.delete(f"/groups/exit/{group.id}/{outsider.id}")

        assert resp.status_code >= 400

    async def test_nonexistent_group_returns_error(
        self,
        authorized_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="ex_bob3")
        await db_session.commit()

        resp = await authorized_client.delete(f"/groups/exit/999999/{bob.id}")

        assert resp.status_code >= 400

    async def test_unauthenticated_request_returns_401(
        self,
        client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob   = await _make_user(db_session, name="Bob", username="ex_bob4")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await client.delete(f"/groups/exit/{group.id}/{bob.id}")

        assert resp.status_code == 401


# ── DELETE /groups/delete/{modifier_id}/{group_id} ───────────────────────────

class TestDeleteGroup:

    async def test_admin_can_delete_group(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        group = await _make_group(db_session, admin=user_a, name="Doomed")

        resp = await authorized_client.delete(f"/groups/delete/{user_a.id}/{group.id}")

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_deleted_group_is_no_longer_retrievable(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        group = await _make_group(db_session, admin=user_a, name="Gone")

        await authorized_client.delete(f"/groups/delete/{user_a.id}/{group.id}")

        info = await authorized_client.get(f"/groups/get_group_info/{group.id}")
        assert info.status_code >= 400

    async def test_non_admin_member_cannot_delete_group(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob   = await _make_user(db_session, name="Bob", username="del_bob1")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await authorized_client.delete(f"/groups/delete/{bob.id}/{group.id}")

        assert resp.status_code >= 400

    async def test_user_not_in_group_cannot_delete(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        outsider = await _make_user(db_session, name="Outsider", username="del_out1")
        group    = await _make_group(db_session, admin=user_a)

        resp = await authorized_client.delete(
            f"/groups/delete/{outsider.id}/{group.id}"
        )

        assert resp.status_code >= 400

    async def test_nonexistent_group_returns_error(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
    ) -> None:
        resp = await authorized_client.delete(
            f"/groups/delete/{user_a.id}/999999"
        )

        assert resp.status_code >= 400

    async def test_delete_removes_group_messages_and_receipts(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        """Cascade: after deletion the group must not be retrievable."""
        bob   = await _make_user(db_session, name="Bob", username="del_bob2")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        # Seed a group message + receipt so the cascade DELETE paths are exercised
        msg = DB_models.groupMessage(
            fromId=user_a.id, toId=group.id, body="Hello",
        )
        db_session.add(msg)
        await db_session.flush()
        await db_session.refresh(msg)
        db_session.add(DB_models.messageReceipt(groupMessageId=msg.id, userId=bob.id))
        await db_session.commit()

        delete_resp = await authorized_client.delete(
            f"/groups/delete/{user_a.id}/{group.id}"
        )
        assert delete_resp.status_code == 200

        info = await authorized_client.get(f"/groups/get_group_info/{group.id}")
        assert info.status_code >= 400

    async def test_unauthenticated_request_returns_401(
        self,
        client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        group = await _make_group(db_session, admin=user_a)

        resp = await client.delete(f"/groups/delete/{user_a.id}/{group.id}")

        assert resp.status_code == 401


# ── POST /groups/remove_member/{modifier_id}/{group_id} ───────────────────────

class TestRemoveMember:

    async def test_admin_can_remove_a_member(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="rm_bob1")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await authorized_client.post(
            f"/groups/remove_member/{user_a.id}/{group.id}",
            json=[bob.id],
        )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_removed_member_no_longer_in_group_info(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="rm_bob2")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        await authorized_client.post(
            f"/groups/remove_member/{user_a.id}/{group.id}",
            json=[bob.id],
        )

        info = await authorized_client.get(f"/groups/get_group_info/{group.id}")
        assert info.status_code == 200
        member_ids = {m["id"] for m in info.json()["members"]}
        assert bob.id not in member_ids

    async def test_admin_remains_in_group_after_removing_others(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="rm_bob3")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        await authorized_client.post(
            f"/groups/remove_member/{user_a.id}/{group.id}",
            json=[bob.id],
        )

        info = await authorized_client.get(f"/groups/get_group_info/{group.id}")
        assert info.status_code == 200
        member_ids = {m["id"] for m in info.json()["members"]}
        assert user_a.id in member_ids

    async def test_admin_can_remove_multiple_members_at_once(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob   = await _make_user(db_session, name="Bob",   username="rm_bob4")
        carol = await _make_user(db_session, name="Carol", username="rm_carol4")
        group = await _make_group(db_session, admin=user_a, members=[bob, carol])

        resp = await authorized_client.post(
            f"/groups/remove_member/{user_a.id}/{group.id}",
            json=[bob.id, carol.id],
        )

        assert resp.status_code == 200
        info = await authorized_client.get(f"/groups/get_group_info/{group.id}")
        member_ids = {m["id"] for m in info.json()["members"]}
        assert bob.id   not in member_ids
        assert carol.id not in member_ids

    async def test_non_admin_member_cannot_remove_others(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob   = await _make_user(db_session, name="Bob",   username="rm_bob5")
        carol = await _make_user(db_session, name="Carol", username="rm_carol5")
        group = await _make_group(db_session, admin=user_a, members=[bob, carol])

        resp = await authorized_client.post(
            f"/groups/remove_member/{bob.id}/{group.id}",
            json=[carol.id],
        )

        assert resp.status_code >= 400

    async def test_user_not_in_group_cannot_remove_members(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        outsider = await _make_user(db_session, name="Outsider", username="rm_out1")
        bob      = await _make_user(db_session, name="Bob",      username="rm_bob6")
        group    = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await authorized_client.post(
            f"/groups/remove_member/{outsider.id}/{group.id}",
            json=[bob.id],
        )

        assert resp.status_code >= 400

    async def test_nonexistent_group_returns_error(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="rm_bob7")
        await db_session.commit()

        resp = await authorized_client.post(
            f"/groups/remove_member/{user_a.id}/999999",
            json=[bob.id],
        )

        assert resp.status_code >= 400

    async def test_removing_nonexistent_user_id_is_a_noop(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        """
        The handler issues a bulk DELETE with userId.in_(user_ids).
        If none of the IDs match any mapTable row the DELETE affects zero
        rows but the endpoint should still return success — no crash.
        """
        group = await _make_group(db_session, admin=user_a)

        resp = await authorized_client.post(
            f"/groups/remove_member/{user_a.id}/{group.id}",
            json=[999999],
        )

        assert resp.status_code == 200

    async def test_unauthenticated_request_returns_401(
        self,
        client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob   = await _make_user(db_session, name="Bob", username="rm_bob8")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await client.post(
            f"/groups/remove_member/{user_a.id}/{group.id}",
            json=[bob.id],
        )

        assert resp.status_code == 401


# ── POST /groups/make_admin/{modifier_id}/{group_id} ──────────────────────────

class TestMakeAdmin:

    async def test_admin_can_promote_a_member(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob   = await _make_user(db_session, name="Bob", username="ma_bob1")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await authorized_client.post(
            f"/groups/make_admin/{user_a.id}/{group.id}",
            params={"user_id": bob.id},
        )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_promoted_member_can_perform_admin_actions(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        """After promotion Bob must be able to rename the group."""
        bob   = await _make_user(db_session, name="Bob", username="ma_bob2")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        promote = await authorized_client.post(
            f"/groups/make_admin/{user_a.id}/{group.id}",
            params={"user_id": bob.id},
        )
        assert promote.status_code == 200

        rename = await authorized_client.put(
            f"/groups/update/{bob.id}/{group.id}",
            json={"name": "Bob renamed this", "description": "desc"},
        )
        assert rename.status_code == 200

    async def test_non_admin_cannot_promote_others(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob   = await _make_user(db_session, name="Bob",   username="ma_bob3")
        carol = await _make_user(db_session, name="Carol", username="ma_carol3")
        group = await _make_group(db_session, admin=user_a, members=[bob, carol])

        resp = await authorized_client.post(
            f"/groups/make_admin/{bob.id}/{group.id}",
            params={"user_id": carol.id},
        )

        assert resp.status_code >= 400

    async def test_user_not_in_group_cannot_promote(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        outsider = await _make_user(db_session, name="Outsider", username="ma_out1")
        bob      = await _make_user(db_session, name="Bob",      username="ma_bob4")
        group    = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await authorized_client.post(
            f"/groups/make_admin/{outsider.id}/{group.id}",
            params={"user_id": bob.id},
        )

        assert resp.status_code >= 400

    async def test_promoting_already_admin_is_idempotent(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        """Promoting an existing admin again must not error — UPDATE sets admin=True on an already-True row."""
        bob   = await _make_user(db_session, name="Bob", username="ma_bob5")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        # First promotion
        first = await authorized_client.post(
            f"/groups/make_admin/{user_a.id}/{group.id}",
            params={"user_id": bob.id},
        )
        assert first.status_code == 200

        # Second promotion of the same user
        second = await authorized_client.post(
            f"/groups/make_admin/{user_a.id}/{group.id}",
            params={"user_id": bob.id},
        )
        assert second.status_code == 200

    async def test_nonexistent_group_returns_error(
        self,
        authorized_client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = await _make_user(db_session, name="Bob", username="ma_bob6")
        await db_session.commit()

        resp = await authorized_client.post(
            f"/groups/make_admin/{user_a.id}/999999",
            params={"user_id": bob.id},
        )

        assert resp.status_code >= 400

    async def test_unauthenticated_request_returns_401(
        self,
        client: AsyncClient,
        user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob   = await _make_user(db_session, name="Bob", username="ma_bob7")
        group = await _make_group(db_session, admin=user_a, members=[bob])

        resp = await client.post(
            f"/groups/make_admin/{user_a.id}/{group.id}",
            params={"user_id": bob.id},
        )

        assert resp.status_code == 401