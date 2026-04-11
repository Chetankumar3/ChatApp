"""
Integration tests for public authentication endpoints and JWT gating.

Public endpoints (no JWT) — all use ``client``:
  POST /login/credentials
  POST /recruiter/register
  POST /register

JWT-gating tests — use ``client`` deliberately (no token) to confirm
protected routes reject bad or absent credentials. ``GET /get_all_users``
is used as a stable probe because it is protected by ``get_current_user``
and has no side-effects.
"""
from __future__ import annotations

import bcrypt
import jwt as pyjwt
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import DB_models


# ── helpers ───────────────────────────────────────────────────────────────────

async def _seed_credentials_user(
    db_session: AsyncSession,
    *,
    username: str,
    password: str,
    name: str = "Test User",
    email: str | None = None,
) -> DB_models.user:
    """Insert a user row + matching passwords row, return the user."""
    email = email or f"{username}@test.com"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = DB_models.user(
        name=name, email=email, username=username,
        displayPictureUrl=f"http://example.com/{username}.png",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    db_session.add(DB_models.passwords(
        userId=user.id, username=username, hashedPassword=hashed,
    ))
    await db_session.commit()
    return user


# ── POST /login/credentials ───────────────────────────────────────────────────

class TestCredentialsLogin:

    async def test_valid_credentials_return_token_and_is_new_user_false(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _seed_credentials_user(db_session, username="alice_login", password="s3cr3t")

        resp = await client.post(
            "/login/credentials",
            json={"username": "alice_login", "password": "s3cr3t"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body
        assert isinstance(body["token"], str) and body["token"]
        assert body["isNewUser"] is False

    async def test_wrong_password_is_rejected(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _seed_credentials_user(db_session, username="alice_wp", password="correct")

        resp = await client.post(
            "/login/credentials",
            json={"username": "alice_wp", "password": "wrong"},
        )

        assert resp.status_code >= 400

    async def test_nonexistent_username_is_rejected(
        self, client: AsyncClient,
    ) -> None:
        resp = await client.post(
            "/login/credentials",
            json={"username": "ghost", "password": "anything"},
        )

        assert resp.status_code >= 400

    async def test_missing_password_field_returns_422(
        self, client: AsyncClient,
    ) -> None:
        resp = await client.post("/login/credentials", json={"username": "only"})

        assert resp.status_code == 422

    async def test_empty_username_is_rejected(
        self, client: AsyncClient,
    ) -> None:
        resp = await client.post(
            "/login/credentials",
            json={"username": "", "password": "pass"},
        )

        assert resp.status_code >= 400


# ── POST /recruiter/register ──────────────────────────────────────────────────

class TestRecruiterRegister:

    async def test_new_recruiter_receives_token_and_is_new_user_false(
        self, client: AsyncClient,
    ) -> None:
        resp = await client.post(
            "/recruiter/register",
            json={
                "username": "rec1", "password": "pass123",
                "name": "Recruiter One", "email": "rec1@test.com",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body
        assert isinstance(body["token"], str) and body["token"]
        assert body["isNewUser"] is False

    async def test_duplicate_username_is_rejected(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _seed_credentials_user(db_session, username="taken_rec", password="p")

        resp = await client.post(
            "/recruiter/register",
            json={
                "username": "taken_rec", "password": "other",
                "name": "Dupe", "email": "dupe@test.com",
            },
        )

        assert resp.status_code >= 400

    async def test_missing_required_fields_return_422(
        self, client: AsyncClient,
    ) -> None:
        # name and email are required by RegisterCredentials
        resp = await client.post(
            "/recruiter/register",
            json={"username": "x", "password": "x"},
        )

        assert resp.status_code == 422

    async def test_registered_recruiter_can_then_log_in(
        self, client: AsyncClient,
    ) -> None:
        creds = {
            "username": "rec_roundtrip", "password": "mypass",
            "name": "RT Rec", "email": "rt@test.com",
        }
        reg = await client.post("/recruiter/register", json=creds)
        assert reg.status_code == 200

        login = await client.post(
            "/login/credentials",
            json={"username": creds["username"], "password": creds["password"]},
        )

        assert login.status_code == 200
        assert "token" in login.json()

    async def test_two_distinct_usernames_both_succeed(
        self, client: AsyncClient,
    ) -> None:
        for tag in ("alpha", "beta"):
            resp = await client.post(
                "/recruiter/register",
                json={
                    "username": f"rec_{tag}", "password": "p",
                    "name": tag.title(), "email": f"{tag}@test.com",
                },
            )
            assert resp.status_code == 200, f"failed for tag={tag!r}"


# ── POST /register ────────────────────────────────────────────────────────────

class TestRegister:

    async def test_new_user_receives_token(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/register",
            json={
                "username": "newuser", "password": "pass",
                "name": "New User", "email": "new@test.com",
            },
        )

        assert resp.status_code == 200
        assert "token" in resp.json()

    async def test_duplicate_username_is_rejected(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _seed_credentials_user(db_session, username="taken_user", password="p")

        resp = await client.post(
            "/register",
            json={
                "username": "taken_user", "password": "other",
                "name": "Dup", "email": "dup@test.com",
            },
        )

        assert resp.status_code >= 400

    async def test_missing_required_fields_return_422(
        self, client: AsyncClient,
    ) -> None:
        resp = await client.post(
            "/register",
            json={"username": "nopass", "name": "No Pass", "email": "x@x.com"},
        )

        assert resp.status_code == 422

    async def test_registered_user_can_then_log_in(
        self, client: AsyncClient,
    ) -> None:
        creds = {
            "username": "user_rt", "password": "rtpass",
            "name": "RT User", "email": "rt@test.com",
        }
        reg = await client.post("/register", json=creds)
        assert reg.status_code == 200

        login = await client.post(
            "/login/credentials",
            json={"username": creds["username"], "password": creds["password"]},
        )

        assert login.status_code == 200
        assert "token" in login.json()


# ── JWT gating ────────────────────────────────────────────────────────────────

class TestJWTGating:
    """Every test uses bare ``client`` (no Authorization header)."""

    PROBE = "/get_all_users"

    async def test_no_authorization_header_returns_401(
        self, client: AsyncClient,
    ) -> None:
        resp = await client.get(self.PROBE)

        assert resp.status_code == 401

    async def test_malformed_bearer_value_returns_401(
        self, client: AsyncClient,
    ) -> None:
        resp = await client.get(
            self.PROBE, headers={"Authorization": "Bearer not.a.real.jwt"},
        )

        assert resp.status_code == 401

    async def test_expired_token_returns_401(
        self, expired_token, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        user = DB_models.user(
            name="Exp User", email="exp@test.com", username="expuser",
            displayPictureUrl="http://example.com/exp.png",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        resp = await client.get(
            self.PROBE,
            headers={"Authorization": f"Bearer {expired_token(user.id)}"},
        )

        assert resp.status_code == 401

    async def test_token_signed_with_wrong_secret_returns_401(
            self, make_token, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        user = DB_models.user(
            name="Sec User", email="sec@test.com", username="secuser",
            displayPictureUrl="http://example.com/sec.png",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        bad_token = pyjwt.encode(
            {"user_id": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            key="wrong-secret",
            algorithm="HS256",
        )
        resp = await client.get(
            self.PROBE,
            headers={"Authorization": f"Bearer {bad_token}"},
        )

        assert resp.status_code == 401

    async def test_valid_token_for_nonexistent_user_returns_401(
        self, make_token, client: AsyncClient,
    ) -> None:
        # Structurally valid JWT but user_id 999999 is not in the DB
        token = make_token(user_id=999_999)
        resp = await client.get(
            self.PROBE,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 401

    async def test_missing_bearer_prefix_returns_401(
        self, make_token, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        user = DB_models.user(
            name="Pre User", email="pre@test.com", username="preuser",
            displayPictureUrl="http://example.com/pre.png",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Token is present but without the "Bearer " prefix
        resp = await client.get(
            self.PROBE,
            headers={"Authorization": make_token(user.id)},
        )

        assert resp.status_code == 401
