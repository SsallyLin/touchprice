import shioaji as sj
from touchprice.core import Base
from touchprice.constant import Trend, PriceType
from typing import Callable


class PriceGap(Base):
    price: float
    trend: Trend


class Price(PriceGap):
    price: float = 0.0
    trend: Trend = Trend.Equal
    price_type: PriceType = PriceType.LimitPrice

    def __init__(
        self,
        price: float = 0.0,
        trend: Trend = Trend.Equal,
        price_type: PriceType = PriceType.LimitPrice,
    ):
        super().__init__(**dict(trend=trend, price=price, price_type=price_type))


class QtyGap(Base):
    qty: int
    trend: Trend


class Qty(QtyGap):
    trend: Trend = Trend.Equal

    def __init__(self, qty: int, trend: Trend = Trend.Equal):
        super().__init__(**dict(qty=qty, trend=trend))


class TouchCmd(Base):
    code: str
    close: Price = None
    buy_price: Price = None
    sell_price: Price = None
    high: Price = None
    low: Price = None
    volume: Qty = None
    total_volume: Qty = None

    def __init__(
        self,
        code: str,
        close: Price = None,
        buy_price: Price = None,
        sell_price: Price = None,
        high: Price = None,
        low: Price = None,
        volume: Qty = None,
        total_volume: Qty = None,
    ):
        super().__init__(
            **dict(
                code=code,
                close=close,
                buy_price=buy_price,
                sell_price=sell_price,
                high=high,
                low=low,
                volume=volume,
                total_volume=total_volume,
            )
        )


class OrderCmd(Base):
    code: str
    order: sj.order.Order

    def __init__(self, code: str, order: sj.order.Order):
        super().__init__(**dict(code=code, order=order))


class TouchOrderCond(Base):
    touch_cmd: TouchCmd
    order_cmd: OrderCmd

    def __init__(self, touch_cmd: TouchCmd, order_cmd: OrderCmd):
        super().__init__(**dict(touch_cmd=touch_cmd, order_cmd=order_cmd))


class StoreCond(Base):
    close: PriceGap = None
    buy_price: PriceGap = None
    sell_price: PriceGap = None
    high: PriceGap = None
    low: PriceGap = None
    volume: QtyGap = None
    total_volume: QtyGap = None
    order_contract: sj.contracts.Contract
    order: sj.Order
    result: Callable = print
    excuted: bool = False


class StatusInfo(Base):
    close: float
    buy_price: float
    sell_price: float
    high: float
    low: float
    change_price: float  # 漲跌
    change_rate: float  # 幅度
    volume: int
    total_volume: int
