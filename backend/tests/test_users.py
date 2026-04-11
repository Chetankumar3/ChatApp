"""
Integration tests for the ``/users`` router.

All three endpoints declare ``Depends(get_current_user)`` → use
``authorized_client`` for authenticated tests and bare ``client`` for
the 401-rejection assertions.

``user_a`` (Alice) is automatically present whenever ``authorized_client``
is requested.  Any other required state (Bob, messages, groups) is seeded
directly in the test body via ``db_session``.

Endpoint coverage
-----------------
  GET  /users/get_user_info/{userId}
  POST /users/change_username/{userId}
  GET  /users/get_all_conversations/{userId}
"""
from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import DB_models


# ── GET /users/get_user_info/{userId} ─────────────────────────────────────────

class TestGetUserInfo:

    async def test_own_profile_returns_correct_fields(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
    ) -> None:
        resp = await authorized_client.get(f"/users/get_user_info/{user_a.id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == user_a.id
        assert body["name"] == user_a.name
        assert body["email"] == user_a.email
        assert body["username"] == user_a.username

    async def test_other_users_profile_is_accessible(
        self, authorized_client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        bob = DB_models.user(
            name="Bob", email="bob@test.com", username="bob",
            displayPictureUrl="http://example.com/bob.png",
        )
        db_session.add(bob)
        await db_session.commit()
        await db_session.refresh(bob)

        resp = await authorized_client.get(f"/users/get_user_info/{bob.id}")

        assert resp.status_code == 200
        assert resp.json()["id"] == bob.id
        assert resp.json()["name"] == "Bob"

    async def test_nonexistent_user_id_returns_error(
        self, authorized_client: AsyncClient,
    ) -> None:
        resp = await authorized_client.get("/users/get_user_info/999999")

        assert resp.status_code >= 400

    async def test_unauthenticated_request_returns_401(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        user = DB_models.user(
            name="Plain", email="plain@test.com", username="plain",
            displayPictureUrl="http://example.com/plain.png",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        resp = await client.get(f"/users/get_user_info/{user.id}")

        assert resp.status_code == 401


# ── POST /users/change_username/{userId} ──────────────────────────────────────

class TestChangeUsername:

    async def test_username_updated_successfully(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
    ) -> None:
        resp = await authorized_client.post(
            f"/users/change_username/{user_a.id}",
            json={"newUsername": "alice_renamed"},
        )

        assert resp.status_code == 200

    async def test_new_username_visible_via_get_user_info(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
    ) -> None:
        new_name = "alice_v2"
        change = await authorized_client.post(
            f"/users/change_username/{user_a.id}",
            json={"newUsername": new_name},
        )
        assert change.status_code == 200

        info = await authorized_client.get(f"/users/get_user_info/{user_a.id}")

        assert info.status_code == 200
        assert info.json()["username"] == new_name

    async def test_successive_renames_keep_only_the_latest(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
    ) -> None:
        for name in ("first", "second", "final"):
            resp = await authorized_client.post(
                f"/users/change_username/{user_a.id}",
                json={"newUsername": name},
            )
            assert resp.status_code == 200

        info = await authorized_client.get(f"/users/get_user_info/{user_a.id}")
        assert info.json()["username"] == "final"

    async def test_missing_new_username_field_returns_422(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
    ) -> None:
        resp = await authorized_client.post(
            f"/users/change_username/{user_a.id}",
            json={},
        )

        assert resp.status_code == 422

    async def test_unauthenticated_request_returns_401(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        user = DB_models.user(
            name="Plain", email="plain@test.com", username="plain",
            displayPictureUrl="http://example.com/plain.png",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        resp = await client.post(
            f"/users/change_username/{user.id}",
            json={"newUsername": "hacked"},
        )

        assert resp.status_code == 401


# ── GET /users/get_all_conversations/{userId} ─────────────────────────────────

class TestGetAllConversations:

    async def test_user_with_no_activity_gets_empty_response(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
    ) -> None:
        resp = await authorized_client.get(
            f"/users/get_all_conversations/{user_a.id}",
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["direct_messages"] == []
        assert body["associated_groups"] == []

    async def test_sent_and_received_direct_messages_are_returned(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = DB_models.user(
            name="Bob", email="bob@test.com", username="bob",
            displayPictureUrl="http://example.com/bob.png",
        )
        db_session.add(bob)
        await db_session.flush()
        await db_session.refresh(bob)

        db_session.add_all([
            DB_models.message(fromId=user_a.id, toId=bob.id, body="Hey Bob!"),
            DB_models.message(fromId=bob.id, toId=user_a.id, body="Hey Alice!"),
            DB_models.message(fromId=user_a.id, toId=bob.id, body="How are you?"),
        ])
        await db_session.commit()

        resp = await authorized_client.get(
            f"/users/get_all_conversations/{user_a.id}",
        )

        assert resp.status_code == 200
        assert len(resp.json()["direct_messages"]) == 3

    async def test_dm_partner_is_listed_in_associated_users(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = DB_models.user(
            name="Bob", email="bob@test.com", username="bob",
            displayPictureUrl="http://example.com/bob.png",
        )
        db_session.add(bob)
        await db_session.flush()
        await db_session.refresh(bob)

        db_session.add(DB_models.message(fromId=user_a.id, toId=bob.id, body="Hi"))
        await db_session.commit()

        resp = await authorized_client.get(
            f"/users/get_all_conversations/{user_a.id}",
        )

        assert resp.status_code == 200
        partner_ids = {u["id"] for u in resp.json()["associated_users"]}
        assert bob.id in partner_ids

    async def test_group_membership_appears_in_associated_groups(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        group = DB_models.group(name="Chat Group", description="A test group")
        db_session.add(group)
        await db_session.flush()
        await db_session.refresh(group)

        db_session.add(DB_models.mapTable(
            groupId=group.id, userId=user_a.id, admin=True,
        ))
        await db_session.commit()

        resp = await authorized_client.get(
            f"/users/get_all_conversations/{user_a.id}",
        )

        assert resp.status_code == 200
        group_ids = {g["id"] for g in resp.json()["associated_groups"]}
        assert group.id in group_ids

    async def test_group_messages_keyed_by_group_id_in_response(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        group = DB_models.group(name="Msg Group", description="desc")
        db_session.add(group)
        await db_session.flush()
        await db_session.refresh(group)

        db_session.add(DB_models.mapTable(groupId=group.id, userId=user_a.id, admin=True))
        await db_session.flush()

        db_session.add_all([
            DB_models.groupMessage(fromId=user_a.id, toId=group.id, body="Hello group"),
            DB_models.groupMessage(fromId=user_a.id, toId=group.id, body="Anyone there?"),
        ])
        await db_session.commit()

        resp = await authorized_client.get(
            f"/users/get_all_conversations/{user_a.id}",
        )

        assert resp.status_code == 200
        group_msgs = resp.json()["group_messages"]
        assert str(group.id) in group_msgs
        assert len(group_msgs[str(group.id)]) == 2

    async def test_unauthenticated_request_returns_401(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        user = DB_models.user(
            name="Plain", email="plain@test.com", username="plain",
            displayPictureUrl="http://example.com/plain.png",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        resp = await client.get(f"/users/get_all_conversations/{user.id}")

        assert resp.status_code == 401
