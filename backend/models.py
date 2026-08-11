from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List


class Group(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    currency: str = "BYN"
    owner_tg_id: int

    members: List["Member"] = Relationship(back_populates="group")
    expenses: List["Expense"] = Relationship(back_populates="group")


class Member(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id")
    tg_id: Optional[int] = None  # заполняется, когда участник открыл мини-апп сам
    display_name: str

    group: Optional[Group] = Relationship(back_populates="members")


class Expense(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id")
    description: str
    amount: float
    payer_member_id: int
    split_among: str  # JSON-список member_id, храним строкой для простоты SQLite

    group: Optional[Group] = Relationship(back_populates="expenses")
