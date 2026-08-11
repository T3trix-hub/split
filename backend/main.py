"""
Бэкенд для мини-аппа «Скинулись».

Запуск:
    pip install -r requirements.txt
    export BOT_TOKEN=...
    uvicorn backend.main:app --reload --port 8000

Мини-апп (webapp/index.html) обращается сюда с заголовком
X-Telegram-Init-Data, взятым из Telegram.WebApp.initData на фронте.
"""
import json
from collections import defaultdict
from typing import List

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, create_engine, select
from pydantic import BaseModel

from .models import Group, Member, Expense
from .auth import validate_init_data

engine = create_engine("sqlite:///splitwise.db")
SQLModel.metadata.create_all(engine)

app = FastAPI(title="Скинулись API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # в проде указать домен мини-аппа
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_session():
    with Session(engine) as session:
        yield session


def get_current_user(x_telegram_init_data: str = Header(...)) -> dict:
    try:
        return validate_init_data(x_telegram_init_data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ---------- schemas ----------
class GroupCreate(BaseModel):
    name: str
    currency: str = "BYN"
    members: List[str]


class ExpenseCreate(BaseModel):
    description: str
    amount: float
    payer_member_id: int
    split_among_member_ids: List[int]


# ---------- routes ----------
@app.post("/api/groups")
def create_group(payload: GroupCreate, session: Session = Depends(get_session),
                  user: dict = Depends(get_current_user)):
    group = Group(name=payload.name, currency=payload.currency, owner_tg_id=user.get("id", 0))
    session.add(group)
    session.commit()
    session.refresh(group)

    for name in payload.members:
        session.add(Member(group_id=group.id, display_name=name))
    session.commit()

    return {"id": group.id}


@app.get("/api/groups/{group_id}")
def get_group(group_id: int, session: Session = Depends(get_session),
              user: dict = Depends(get_current_user)):
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(404, "Группа не найдена")

    members = session.exec(select(Member).where(Member.group_id == group_id)).all()
    expenses = session.exec(select(Expense).where(Expense.group_id == group_id)).all()

    return {
        "id": group.id,
        "name": group.name,
        "currency": group.currency,
        "members": [{"id": m.id, "name": m.display_name} for m in members],
        "expenses": [
            {
                "id": e.id,
                "description": e.description,
                "amount": e.amount,
                "payer_member_id": e.payer_member_id,
                "split_among": json.loads(e.split_among),
            }
            for e in expenses
        ],
    }


@app.post("/api/groups/{group_id}/expenses")
def add_expense(group_id: int, payload: ExpenseCreate, session: Session = Depends(get_session),
                 user: dict = Depends(get_current_user)):
    expense = Expense(
        group_id=group_id,
        description=payload.description,
        amount=payload.amount,
        payer_member_id=payload.payer_member_id,
        split_among=json.dumps(payload.split_among_member_ids),
    )
    session.add(expense)
    session.commit()
    return {"id": expense.id}


@app.get("/api/groups/{group_id}/settlement")
def get_settlement(group_id: int, session: Session = Depends(get_session),
                    user: dict = Depends(get_current_user)):
    """Возвращает баланс каждого участника и минимальный набор переводов для закрытия долгов."""
    members = session.exec(select(Member).where(Member.group_id == group_id)).all()
    expenses = session.exec(select(Expense).where(Expense.group_id == group_id)).all()

    balance = defaultdict(float)
    for e in expenses:
        who = json.loads(e.split_among)
        share = e.amount / len(who)
        balance[e.payer_member_id] += e.amount
        for m_id in who:
            balance[m_id] -= share

    creditors = sorted(
        [(m_id, amt) for m_id, amt in balance.items() if amt > 0.01],
        key=lambda x: -x[1],
    )
    debtors = sorted(
        [(m_id, -amt) for m_id, amt in balance.items() if amt < -0.01],
        key=lambda x: -x[1],
    )

    name_by_id = {m.id: m.display_name for m in members}
    transactions = []
    i, j = 0, 0
    creditors, debtors = list(creditors), list(debtors)
    while i < len(debtors) and j < len(creditors):
        d_id, d_amt = debtors[i]
        c_id, c_amt = creditors[j]
        pay = min(d_amt, c_amt)
        transactions.append({
            "from": name_by_id[d_id],
            "to": name_by_id[c_id],
            "amount": round(pay, 2),
        })
        d_amt -= pay
        c_amt -= pay
        debtors[i] = (d_id, d_amt)
        creditors[j] = (c_id, c_amt)
        if d_amt < 0.01:
            i += 1
        if c_amt < 0.01:
            j += 1

    return {
        "balances": [
            {"member_id": m_id, "name": name_by_id[m_id], "balance": round(amt, 2)}
            for m_id, amt in balance.items()
        ],
        "transactions": transactions,
    }
