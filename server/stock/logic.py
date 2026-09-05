import sqlmodel as sql

from .models import Stock, StockEntry
from user.models import User, Holding, Transaction
from data.cache import Cache

def sumGP(a: float, n: int) -> float:
    return a * (1 - a**n) / (1 - a)

def get_current_price(stock: Stock, session: sql.Session) -> float:
    try:
        return StockEntry.from_json(stock.uid, Cache().get(stock.uid.hex)).close
    except Exception:
        entry = session.exec(
            sql.select(StockEntry)
            .where(StockEntry.stock_id == stock.uid)
            .order_by(StockEntry.timestamp.desc())  # type: ignore
            .limit(1)
        ).first()
        if entry is None:
            raise ValueError(f"No price data available for stock {stock.uid}")
        return entry.close

def buy_stock(
    user: User, stock: Stock, units: int,
    session: sql.Session, holding: Holding | None
):
    per_unit = get_current_price(stock, session)
    txn = Transaction(
        user=user.uid,
        stock=stock.uid,
        num_units=units,
        price=per_unit
    )

    if holding is not None and holding.quantity < 0:
        num_units = min(units, -holding.quantity)
        short_price = holding.short_balance / -holding.quantity
        profit = num_units * (short_price - per_unit)

        user.balance += profit + (num_units * short_price)
        holding.short_balance -= num_units * short_price
        holding.quantity += num_units
        units -= num_units

    
    if units > 0:
        price = per_unit * sumGP(1.001, units)
        if (user.balance < price):
            return { "valid": False, "message": "Insufficient balance" }
        
        user.balance -= price
        if holding is None:
            holding = Holding(
                user=user.uid,
                stock=stock.uid,
                quantity=units,
                short_balance=0,
                avg_price=price/units
            )
        else:
            holding.avg_price = (holding.avg_price * holding.quantity + price) / (holding.quantity + units)
            holding.quantity += units
        
        holding.save(session)

    user.save(session)
    txn.save(session)
    return { 
        "valid": True, "message": "Transaction successful!", 
        "balance": user.balance, "avg_price": holding.avg_price # type: ignore
    }


def sell_stock(
    user: User, stock: Stock, units: int,
    session: sql.Session, holding: Holding | None
):
    per_unit = get_current_price(stock, session)
    txn = Transaction(
        user=user.uid,
        stock=stock.uid,
        num_units=-units,
        price=per_unit
    )
    
    if holding is not None:
        num_units = min(holding.quantity, units)
        price = per_unit * sumGP(1/1.001, num_units)

        user.balance += price
        holding.quantity -= num_units
        units -= num_units
    
    if units > 0:
        price = per_unit * sumGP(1/1.001, units)
        if (user.balance < price):
            return { "valid": False, "message": "Insufficient balance" }
        
        user.balance -= price
        if holding is None:
            holding = Holding(
                user=user.uid,
                stock=stock.uid,
                quantity=-units,
                short_balance=price,
                avg_price=price/units
            )
        else:
            holding.avg_price = (holding.avg_price * -holding.quantity + price) / (-holding.quantity + units)
            holding.quantity -= units
            holding.short_balance += price
            
        holding.save(session)

    user.save(session)
    txn.save(session)
    return { 
        "valid": True, "message": "Transaction successful!", 
        "balance": user.balance, "avg_price": holding.avg_price # type: ignore
    }
        