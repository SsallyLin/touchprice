import typing
import shioaji as sj
from pydantic import BaseModel
from touchprice.constant import Trend, PriceType
from typing import Callable
from decimal import Decimal


class PriceGap(BaseModel):
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


class QtyGap(BaseModel):
    qty: int
    trend: Trend


class Qty(QtyGap):
    trend: Trend = Trend.Equal

    def __init__(self, qty: int, trend: Trend = Trend.Equal):
        super().__init__(**dict(qty=qty, trend=trend))


class TouchCmd(BaseModel):
    code: str
    close: typing.Optional[Price] = None
    buy_price: typing.Optional[Price] = None
    sell_price: typing.Optional[Price] = None
    high: typing.Optional[Price] = None
    low: typing.Optional[Price] = None
    volume: typing.Optional[Qty] = None
    total_volume: typing.Optional[Qty] = None
    ask_volume: typing.Optional[Qty] = None
    bid_volume: typing.Optional[Qty] = None

    def __init__(
        self,
        code: str,
        close: typing.Optional[Price] = None,
        buy_price: typing.Optional[Price] = None,
        sell_price: typing.Optional[Price] = None,
        high: typing.Optional[Price] = None,
        low: typing.Optional[Price] = None,
        volume: typing.Optional[Qty] = None,
        total_volume: typing.Optional[Qty] = None,
        ask_volume: typing.Optional[Qty] = None,
        bid_volume: typing.Optional[Qty] = None,
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
                ask_volume=ask_volume,
                bid_volume=bid_volume,
            )
        )

    def __repr_args__(self):
        return [(k, v) for k, v in self._iter(to_dict=False, exclude_defaults=True)]


class OrderCmd(BaseModel):
    code: str
    order: sj.order.Order

    def __init__(self, code: str, order: sj.order.Order):
        super().__init__(**dict(code=code, order=order))


class LossProfitCmd(BaseModel):
    loss_pricegap: PriceGap = None
    loss_order: sj.Order = None
    profit_pricegap: PriceGap = None
    profit_order: sj.Order = None


class StoreLossProfit(BaseModel):
    loss_close: PriceGap = None
    profit_close: PriceGap = None
    order_contract: sj.contracts.Contract
    loss_order: sj.Order = None
    profit_order: sj.Order = None
    result: sj.order.Trade = None
    excuted_cb: Callable[[sj.order.Trade], sj.order.Trade] = print
    excuted: bool = False


class TouchOrderCond(BaseModel):
    touch_cmd: TouchCmd
    order_cmd: OrderCmd

    def __init__(
        self,
        touch_cmd: TouchCmd,
        order_cmd: OrderCmd,
    ):
        super().__init__(
            **dict(
                touch_cmd=touch_cmd,
                order_cmd=order_cmd,
            )
        )


class StoreCond(BaseModel):
    close: typing.Optional[PriceGap] = None
    buy_price: typing.Optional[PriceGap] = None
    sell_price: typing.Optional[PriceGap] = None
    high: typing.Optional[PriceGap] = None
    low: typing.Optional[PriceGap] = None
    volume: typing.Optional[QtyGap] = None
    total_volume: typing.Optional[QtyGap] = None
    ask_volume: typing.Optional[QtyGap] = None
    bid_volume: typing.Optional[QtyGap] = None
    order_contract: sj.contracts.Contract
    order: sj.Order
    result: sj.order.Trade = None
    excuted_cb: Callable[[sj.order.Trade], sj.order.Trade] = print
    excuted: bool = False

    def __repr_args__(self):
        return [(k, v) for k, v in self._iter(to_dict=False, exclude_defaults=True)]


class StatusInfo(BaseModel):
    close: Decimal
    buy_price: Decimal
    sell_price: Decimal
    high: Decimal
    low: Decimal
    change_price: float  # 漲跌
    change_rate: float  # 幅度
    volume: int
    total_volume: int
    ask_volume: int = 0
    bid_volume: int = 0
    add_ts: float = 0
