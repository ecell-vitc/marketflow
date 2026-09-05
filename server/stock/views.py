import sqlmodel as sql
from os import environ
from fastapi import APIRouter, HTTPException, status, Depends, WebSocket, WebSocketDisconnect

import uuid
from . import models, forms
from user import models as user_models
from .stock import StockProvider, Event
from . import logic, patterns
import middleware

from data.db import get_session
from data.socket_pool import SocketPool
from data.cache import Cache


router = APIRouter()
POOL = SocketPool()
PROVIDER = StockProvider(2, 10, POOL)


@router.get('/')
def get_stocks(session: sql.Session = Depends(get_session)):
    res: dict[str, dict] = {}
    rows = session.exec(
        sql.select(models.StockEntry, models.Stock)
           .join(models.Stock)
           .order_by(models.StockEntry.timestamp)# type: ignore
    )

    seen = {}

    for entry, stock in rows:
        stock_id = entry.stock_id.hex

        if stock_id not in res:
            res[stock_id] = {
                'name': stock.name,
                'entries': [],
            }

        data = entry.to_dict()
        if stock_id not in seen: seen[stock_id] = []

        if data['time'] in seen[stock_id]: continue

        res[stock_id]['entries'].append(entry.to_dict())
        seen[stock_id].append(data['time'])
    
    
    if PROVIDER.started.is_set():
        cache = Cache()
        for stock_id in res.keys():
            try:
                entry = models.StockEntry.from_json(uuid.UUID(stock_id), cache.get(stock_id))
            except Exception:
                continue
            res[stock_id]['entries'].append(entry.to_dict())


    return res


@router.websocket('/')
async def connect_websocket(websocket: WebSocket):
    try:
        await websocket.accept()
        POOL.add(websocket)
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        POOL.remove(websocket)


@router.post('/transact/{stock_id}')
def transact(
    stock_id: str, data: forms.TransactForm, session: sql.Session = Depends(get_session),
    user: user_models.User = Depends(middleware.get_user)
):
    if not user.verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"message": "Account not verified"})
    
    stock = session.exec(sql.select(models.Stock).where(models.Stock.uid == uuid.UUID(stock_id))).one_or_none()
    if stock is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"message": "Stock ID not found"})
    
    holding = session.exec(
        sql.select(user_models.Holding)
        .where(user_models.Holding.user == user.uid, user_models.Holding.stock == stock.uid)
    ).one_or_none()

    
    if data.units == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"message": "Units cannot be zero"})
    
    res: dict[str, bool | str] = {}
    try:
        if data.units < 0: res = logic.sell_stock(user, stock, abs(data.units), session, holding)
        else: res = logic.buy_stock(user, stock, data.units, session, holding)
    except ValueError as e:
        raise HTTPException(status.HTTP_428_PRECONDITION_REQUIRED, detail={"message": str(e)})

    if not res['valid']:
        raise HTTPException(status.HTTP_428_PRECONDITION_REQUIRED, detail=res)
    
    return res


@router.post('/')
def start_stock(_: None = Depends(middleware.check_admin)):
    global PROVIDER
    if PROVIDER.started.is_set(): return HTTPException(status.HTTP_428_PRECONDITION_REQUIRED, detail='Stock provider is already initialized')
    
    PROVIDER = StockProvider(2, 10, POOL)
    PROVIDER.start()
    return {"message": "Stock provider initialized"}


@router.delete('/')
def stop_stock(_: None = Depends(middleware.check_admin)):
    if not PROVIDER.started.is_set(): return HTTPException(status.HTTP_428_PRECONDITION_REQUIRED, detail={"message": "Stock provider is not running!"})

    PROVIDER.started.clear()
    PROVIDER.join()
    return {"message": "Stock provider stopped"}

@router.post('/events')
def trigger_event(data: forms.StockEventForm, _: None = Depends(middleware.check_admin)):
    if not PROVIDER.started.is_set(): raise HTTPException(status.HTTP_428_PRECONDITION_REQUIRED, detail={"message": "Stock provider is not running!"})
    for event in data.events:
        PROVIDER.add_pattern(event['id'], [
            Event(
                data_from=models.StockEntry.from_json(
                    uuid.UUID(event['id']), 
                    Cache().get(event['id'])
                ).close, 
                data_to=event['to'],
                num_candles=event['duration']
            )
        ])

    return {"message": "Events added successfully!"}

@router.post('/patterns')
def trigger_pattern(data: forms.StockEventForm, _: None = Depends(middleware.check_admin)):
    if not PROVIDER.started.is_set(): raise HTTPException(status.HTTP_428_PRECONDITION_REQUIRED, detail={"message": "Stock provider is not running!"})

    functions = {
        'bullish_flag': patterns.BULLISH_FLAG,
        'bearish_flag': patterns.BEARISH_FLAG,
        'bullish_pennant': patterns.BULLISH_PENNANT,
        'bearish_pennant': patterns.BEARISH_PENNANT,
        'double_top': patterns.DOUBLE_TOP,
        'double_bottom': patterns.DOUBLE_BOTTOM,
        'head_and_shoulders': patterns.HEAD_AND_SHOULDERS,
        'inverse_head_and_shoulders': patterns.INVERSE_HEAD_AND_SHOULDERS,
        'rising_wedge': patterns.RISING_WEDGE,
        'falling_wedge': patterns.FALLING_WEDGE,
        'rectangle': patterns.RECTANGLE,
        'cup_and_handle': patterns.CUP_AND_HANDLE,
        'inverted_cup_and_handle': patterns.INVERTED_CUP_AND_HANDLE,
    }

    cache = Cache()
    for event in data.events:
        value = models.StockEntry.from_json(
            uuid.UUID(event['id']), 
            cache.get(event['id'])
        ).close

        if event['pattern'] not in functions: continue
        PROVIDER.add_pattern(
            event['id'], 
            functions[event['pattern']](value)
        )

    return {"message": "Patterns added successfully!"}