import sqlmodel as sql
import uuid, json, pytz
from datetime import datetime
from data.db import BaseModel, BaseTimestampModel


class Stock(BaseModel, table=True):
    name: str
    category: str

class StockEntry(BaseTimestampModel, table=True):
    stock_id: uuid.UUID = sql.Field(foreign_key='stock.uid', ondelete='CASCADE')
    open: float
    low: float
    high: float
    close: float

    def __init__(self, stock_id: uuid.UUID, value: float | None = None, **kwargs):
        if (value == None): super().__init__(stock_id=stock_id, **kwargs) # type: ignore
        else: super().__init__(stock_id=stock_id, open=value, close=value, low=value, high=value) # type: ignore

    def set_value(self, value: float):
        if value <= 0: value = 1
        
        self.low = min(self.low, value)
        self.high = max(self.high, value)
        self.close = value

    @classmethod
    def from_json(cls, stock_id: uuid.UUID, json_str: str | None):
        if json_str == None: raise Exception("String cannot be none!")

        data: dict[str, str | float] = json.loads(json_str)
        return cls(
            stock_id=stock_id,
            open=float(data['open']), close=float(data['close']),
            low=float(data['low']), high=float(data['high']),
            timestamp=datetime.fromtimestamp(float(data['time']), tz=pytz.timezone('Asia/Kolkata'))
        )

    def to_dict(self): return {
        "open": self.open, "close": self.close,
        "low": self.low, "high": self.high,
        "time": int(self.timestamp.timestamp())
    }
    
    def __str__(self): return json.dumps(self.to_dict())
