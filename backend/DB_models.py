from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, func, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

class User(Base):
    __tablename__ =  "user"

    Id: Mapped[int] = mapped_column(primary_key=True)
    Username: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=True)
    Name: Mapped[str] = mapped_column(String(20), index=True)
    MobileNumber: Mapped[str] = mapped_column(String(15), nullable=True)
    Email: Mapped[Optional[str]] = mapped_column(String(30))
    ProfilePictureUrl: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class OAuthTable(Base):
    __tablename__ = "oauth_table"

    Id: Mapped[int] = mapped_column(primary_key=True)
    UserId: Mapped[int] = mapped_column(ForeignKey("user.Id"), index=True)
    OAuthId: Mapped[Optional[str]] = mapped_column(String(60), index=True)

class Group(Base):
    __tablename__ =  "group"

    Id: Mapped[int] = mapped_column(primary_key=True)
    Name: Mapped[str] = mapped_column(String(30), index=True)
    Description: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ProfilePictureUrl: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class MapTable(Base):
    __tablename__ =  "map_table"

    Id: Mapped[int] = mapped_column(primary_key=True)
    UserId: Mapped[int] = mapped_column(ForeignKey("user.Id"), index=True)
    GroupId: Mapped[int] = mapped_column(ForeignKey("group.Id"), index=True)

class Message(Base):
    __tablename__ = "message"

    Id: Mapped[int] = mapped_column(primary_key=True)
    FromId: Mapped[int] = mapped_column(ForeignKey("user.Id"), index=True)
    ToId: Mapped[int] = mapped_column(ForeignKey("user.Id"), index=True)
    Body: Mapped[str] = mapped_column(Text)
    SentAt: Mapped[datetime] = mapped_column(server_default=func.now())
    ReceivedAt: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    SeenAt: Mapped[Optional[datetime]] = mapped_column(nullable=True)

class GroupMessage(Base):
    __tablename__ = "group_message"

    Id: Mapped[int] = mapped_column(primary_key=True)
    FromId: Mapped[int] = mapped_column(ForeignKey("user.Id"), index=True)
    ToId: Mapped[int] = mapped_column(ForeignKey("group.Id"), index=True)
    Body: Mapped[str] = mapped_column(Text)
    SentAt: Mapped[datetime] = mapped_column(server_default=func.now())

class MessageReceipt(Base):
    __tablename__ = "message_receipt"

    Id: Mapped[int] = mapped_column(primary_key=True)
    GroupMessageId: Mapped[int] = mapped_column(ForeignKey("group_message.Id"), index=True)
    UserId: Mapped[int] = mapped_column(ForeignKey("user.Id"), index=True)
    ReceivedAt: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    SeenAt: Mapped[Optional[datetime]] = mapped_column(nullable=True)