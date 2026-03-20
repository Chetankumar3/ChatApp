from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

class User(Base):
    __tablename__ =  "user"

    Id: Mapped[int] = mapped_column(primary_key=True)
    Username: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    Name: Mapped[str] = mapped_column(String(20), index=True)
    MobileNumber: Mapped[str] = mapped_column(String(15))
    Email: Mapped[Optional[str]] = mapped_column(String(30))
    ProfilePictureUrl: Mapped[Optional[str]] = mapped_column(Text)

class OAuthTable(Base):
    __tablename__ = "oauth_table"

    Id: Mapped[int] = mapped_column(primary_key=True)
    UserId: Mapped[int] = mapped_column(ForeignKey("user.Id"))
    OAuthId: Mapped[Optional[str]] = mapped_column(String(60), index=True)

class Group(Base):
    __tablename__ =  "group"

    Id: Mapped[int] = mapped_column(primary_key=True)
    Name: Mapped[str] = mapped_column(String(30), index=True)
    Description: Mapped[Optional[str]] = mapped_column(String(100))
    ProfilePictureUrl: Mapped[Optional[str]] = mapped_column(Text)

class MapTable(Base):
    __tablename__ =  "map_table"

    Id: Mapped[int] = mapped_column(primary_key=True)
    UserId: Mapped[int] = mapped_column(ForeignKey("user.Id"), index=True)
    GroupId: Mapped[int] = mapped_column(ForeignKey("group.Id"), index=True)

class Message(Base):
    __tablename__ = "message"

    Id: Mapped[int] = mapped_column(primary_key=True)
    FromId: Mapped[int] = mapped_column(ForeignKey("user.Id"))
    ToId: Mapped[int] = mapped_column(ForeignKey("user.Id"))
    Message: Mapped[str] = mapped_column(Text)
    SentAt: Mapped[datetime] = mapped_column()
    ReceivedAt: Mapped[datetime] = mapped_column()

class GroupMessage(Base):
    __tablename__ = "group_message"

    Id: Mapped[int] = mapped_column(primary_key=True)
    FromId: Mapped[int] = mapped_column(ForeignKey("user.Id"))
    ToId: Mapped[int] = mapped_column(ForeignKey("group.Id"))
    Message: Mapped[str] = mapped_column(Text)
    SentAt: Mapped[datetime] = mapped_column()