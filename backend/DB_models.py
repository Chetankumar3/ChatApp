from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, func, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

class user(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(20), index=True)
    mobileNumber: Mapped[str] = mapped_column(String(15), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(30))
    displayPictureUrl: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class oAuthTable(Base):
    __tablename__ = "oauth_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    userId: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    oauthId: Mapped[Optional[str]] = mapped_column(String(60), index=True)

class group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), index=True)
    description: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    displayPictureUrl: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class mapTable(Base):
    __tablename__ = "map_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin: Mapped[bool] = mapped_column() # true for "admin", false for "member"
    userId: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    groupId: Mapped[int] = mapped_column(ForeignKey("group.id"), index=True)

class message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(primary_key=True)
    fromId: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    toId: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    sentAt: Mapped[datetime] = mapped_column(server_default=func.now())
    receivedAt: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    seenAt: Mapped[Optional[datetime]] = mapped_column(nullable=True)

class groupMessage(Base):
    __tablename__ = "group_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    fromId: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    toId: Mapped[int] = mapped_column(ForeignKey("group.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    sentAt: Mapped[datetime] = mapped_column(server_default=func.now())

class messageReceipt(Base):
    __tablename__ = "message_receipt"

    id: Mapped[int] = mapped_column(primary_key=True)
    groupMessageId: Mapped[int] = mapped_column(ForeignKey("group_message.id"), index=True)
    userId: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    receivedAt: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    seenAt: Mapped[Optional[datetime]] = mapped_column(nullable=True)