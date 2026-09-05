import asyncio, random, threading, time
import sqlmodel as sql
import datetime
from datetime import timedelta
from stock.models import Stock, StockEntry
from user.models import Transaction, User, Holding

from data.socket_pool import SocketPool
from data.cache import Cache
from data.db import get_session


class Event:
    _curr: int
    _prev: float
    num_candles: int
    ends: tuple[float, float]

    def __init__(self, num_candles: int, data_from: float, data_to: float):
        if num_candles < 1: raise ValueError("Number of candles for transition should be atleast 1")

        self._curr = 0
        self._prev = data_from
        self.num_candles = num_candles
        self.ends = (data_from, data_to)

    def is_finished(self) -> bool:
        return self._curr == self.num_candles

    def get_next(self) -> float:
        self._curr += 1
        if self._curr > self.num_candles: raise IndexError("Exceeded the number of candles")
        if self._curr == self.num_candles: return self.ends[1]
        lin_value = self.ends[0] + self._curr * (self.ends[1] - self.ends[0]) / self.num_candles

        diff = min(lin_value - self.ends[0], self.ends[1] - lin_value) / 2
        value = random.uniform(lin_value - diff, lin_value + diff)
        self._prev = value
        return value


class StockProvider(threading.Thread):
    __update: int
    __trigger: int
    __pool: SocketPool

    __events: dict[str, list[Event]]

    started: threading.Event

    def __init__(self, update: int, trigger: int, pool: SocketPool):
        self.__update = update
        self.__trigger = trigger
        self.__pool = pool

        self.__events = {}
        self.started = threading.Event()
    
        super().__init__()

    def add_pattern(self, stock_uid: str, events: list[Event]):
        self.__events[stock_uid] = events

    def __get_update(self, session: sql.Session, stock: Stock, timestamp: datetime.datetime,):
        res = 0
        txns = session.exec(
            sql.select(Transaction)
            .where(
                Transaction.stock == stock.uid,
                Transaction.timestamp >= timestamp
            )
        ).all()

        for txn in txns:
            res += txn.price * 0.001 * (1 if txn.num_units > 0 else -1)
        
        return res

    def broadcast_updates(
        self,  stocks: list[Stock], delta_time: float,
        cache: Cache, session: sql.Session,
        last_candle_update: bool
    ):
        updates = {}
                
        for stock in stocks:
            entry = StockEntry.from_json(stock.uid, cache.get(stock.uid.hex))
            value = entry.close

            if last_candle_update and len(self.__events[stock.uid.hex]) > 0:
                value = self.__events[stock.uid.hex][0].get_next()
                if self.__events[stock.uid.hex][0].is_finished():
                    self.__events[stock.uid.hex].pop(0)
            else:
                value += self.__get_update(
                    session, stock,
                    entry.timestamp + timedelta(seconds=delta_time - self.__update),
                )
                value += value * random.uniform(-0.01, 0.01)
            
            entry.set_value(value)
            updates[stock.uid.hex] = entry.to_dict()
            cache.set(stock.uid.hex, str(entry))
        
        asyncio.run(self.__pool.broadcast(updates))

    

    def run(self):
        if self.started.is_set(): return None
        self.started.set()

        cache = Cache()
        session = next(get_session())
        stocks = list(session.exec(sql.select(Stock)).fetchall())

        for stock in stocks:
            entry = session.exec(
                sql.select(StockEntry)
                .where(StockEntry.stock_id == stock.uid)
                .order_by(StockEntry.timestamp.desc())  # type: ignore
                .limit(1)
            ).first()
            if entry is None: continue

            cache.set(
                stock.uid.hex,
                str(StockEntry(
                    stock.uid,
                    value=entry.close
                ))
            )
            self.__events[stock.uid.hex] = []

        delta_time = 0
        while self.started.is_set():
                        
            if delta_time == self.__trigger:
                delta_time = 0
                new_data = {}
                for stock in stocks:
                    entry = StockEntry.from_json(stock.uid, cache.get(stock.uid.hex))
                    entry.save(session)

                    value = entry.close + self.__get_update(
                        session, stock, 
                        entry.timestamp + timedelta(seconds=self.__trigger - self.__update)
                    ) + abs(entry.open - entry.close) * random.uniform(-0.1, 0.1)
                    
                    new_entry = StockEntry(stock_id=stock.uid, value=value)
                    cache.set(stock.uid.hex, str(new_entry))
                    new_data[stock.uid.hex] = new_entry.to_dict()

                asyncio.run(self.__pool.broadcast(new_data))

            else: self.broadcast_updates(
                stocks, delta_time, cache, session,
                last_candle_update=(delta_time + self.__update == self.__trigger)
            )


            time.sleep(self.__update)
            delta_time += self.__update

        session.close()