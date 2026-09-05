import os, jwt
from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from data import db
from data.cache import Cache
import middleware

import stock.models as stock_models
import user.models as user_models
from user.forms import LoginForm

router = APIRouter()

TEST_USER_PASSWORD = "Testing@123"

class CreateTestUsersForm(BaseModel):
    emails: List[str]

class StockSeed(BaseModel):
    name: str
    category: str
    value: float = 5000.0

class CreateStocksForm(BaseModel):
    stocks: List[StockSeed]

@router.post('/admin/login')
def admin_login(data: LoginForm):
    if data.username != os.environ['ADMIN_USERNAME'] or data.password != os.environ['ADMIN_PASSWORD']:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"message": "Incorrect username or password"})

    token = jwt.encode(
        {"username": data.username, "password": data.password},
        os.environ['SECRET'],
        algorithm='HS256'
    )
    return {"token": token}


@router.post('/admin/test-users')
def create_test_users(
    data: CreateTestUsersForm,
    _: None = Depends(middleware.check_admin),
    session: db.sql.Session = Depends(db.get_session)
):
    created, skipped = [], []

    for email in data.emails:
        existing = session.exec(
            db.sql.select(user_models.User).where(user_models.User.username == email)
        ).one_or_none()

        if existing is not None:
            skipped.append(email)
            continue

        user = user_models.User(username=email, password=TEST_USER_PASSWORD)
        user.verified = True
        user.save(session)
        created.append(email)

    return {"created": created, "skipped": skipped, "password": TEST_USER_PASSWORD}


@router.post('/admin/stocks')
def create_stocks(
    data: CreateStocksForm,
    _: None = Depends(middleware.check_admin),
    session: db.sql.Session = Depends(db.get_session)
):
    created = []

    for seed in data.stocks:
        stock = stock_models.Stock(name=seed.name, category=seed.category)
        stock.save(session)
        stock_models.StockEntry(stock_id=stock.uid, value=seed.value).save(session)
        created.append(seed.name)

    return {"created": created}


@router.get('/leaderboard')
def get_leaderboard(session: db.sql.Session = Depends(db.get_session)):
    res = {}
    for user in session.exec(db.sql.select(user_models.User).where(user_models.User.verified == True)).all():
        res[user.username] = user.balance

    for user, holding in session.exec(
        db.sql.select(user_models.User, user_models.Holding)
        .join(user_models.Holding)
        .where(user_models.User.verified == True)
    ).all():
        cache_entry = Cache().get(holding.stock.hex)
        res[user.username] += holding.quantity * \
            (stock_models.StockEntry.from_json(holding.stock, cache_entry).close if cache_entry else 0)

    return res




from data.socket_pool import SocketPool
import asyncio
from typing import Dict, Any
NEWS_POOL = SocketPool()

@router.websocket('/news/')
async def connect_websocket(websocket: WebSocket):
    try:
        await websocket.accept()
        NEWS_POOL.add(websocket)
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        NEWS_POOL.remove(websocket)
        

@router.post('/news/')
def broadcast_news(
    data: Dict[str, Any],
    _: None = Depends(middleware.check_admin),
):
    if data.get("random", False):
        asyncio.run(NEWS_POOL.random_send(data))
    else:
        asyncio.run(NEWS_POOL.broadcast(data))
    return {"detail": "News broadcasted"}