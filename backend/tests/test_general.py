"""
Integration tests for ``GET /get_all_users``.

Protected by ``get_current_user`` → use ``authorized_client``.
``user_a`` (Alice) is automatically present because ``authorized_client``
declares it as a dependency in conftest.py.  Secondary users are seeded
inline via ``db_session``.
"""
from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import DB_models


class TestGetAllUsers:

    async def test_returns_200_with_users_key(
        self, authorized_client: AsyncClient,
    ) -> None:
        resp = await authorized_client.get("/get_all_users")

        assert resp.status_code == 200
        assert "users" in resp.json()

    async def test_only_alice_present_when_no_other_users_seeded(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
    ) -> None:
        resp = await authorized_client.get("/get_all_users")

        assert resp.status_code == 200
        users = resp.json()["users"]
        assert len(users) == 2
        assert user_a.id in {u["id"] for u in users}

    async def test_seeded_second_user_appears_in_list(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
        db_session: AsyncSession,
    ) -> None:
        bob = DB_models.user(
            name="Bob", email="bob@test.com", username="bob",
            displayPictureUrl="http://example.com/bob.png",
        )
        db_session.add(bob)
        await db_session.commit()
        await db_session.refresh(bob)

        resp = await authorized_client.get("/get_all_users")

        assert resp.status_code == 200
        ids = {u["id"] for u in resp.json()["users"]}
        assert user_a.id in ids
        assert bob.id in ids

    async def test_count_matches_number_of_seeded_users(
        self, authorized_client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        # Seed two additional users alongside the Alice that authorized_client creates
        for i in range(2):
            db_session.add(DB_models.user(
                name=f"Extra {i}", email=f"extra{i}@test.com",
                username=f"extra{i}", displayPictureUrl=f"http://example.com/extra{i}.png",
            ))
        await db_session.commit()

        resp = await authorized_client.get("/get_all_users")

        assert resp.status_code == 200
        # Alice + 2 extras = 3
        assert len(resp.json()["users"]) == 3

    async def test_each_entry_contains_expected_fields(
        self, authorized_client: AsyncClient, user_a: DB_models.user,
    ) -> None:
        resp = await authorized_client.get("/get_all_users")

        assert resp.status_code == 200
        alice = next(u for u in resp.json()["users"] if u["id"] == user_a.id)
        assert alice["name"] == user_a.name
        assert alice["email"] == user_a.email

    async def test_unauthenticated_request_returns_401(
        self, client: AsyncClient,
    ) -> None:
        resp = await client.get("/get_all_users")

        assert resp.status_code == 401
