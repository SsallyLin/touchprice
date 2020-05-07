import shioaji as sj
import typing
from .core import Base
from pydantic import StrictInt
from functools import partial
from enum import Enum


class Trend(str, Enum):
    Up = "Up"
    Down = "Down"
    Equal = "Equal"


class PriceType(str, Enum):
    LimitPrice = "LimitPrice"  # 限價
    LimitUp = "LimitUp"  # 漲停
    Unchanged = "Unchanged"  # 平盤
    LimitDown = "LimitDown"  # 跌停


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


def get_contracts(api: sj.Shioaji):
    contracts = {
        code: contract
        for name, iter_contract in api.Contracts
        for code, contract in iter_contract._code2contract.items()
    }
    return contracts


class TouchOrder:
    def __init__(self, api: sj.Shioaji):
        self.api: sj.Shioaji = api
        self.conditions: typing.Dict[str, typing.List[StoreCond]] = {}
        self.infos: typing.Dict[str, StatusInfo] = {}
        self.contracts: dict = get_contracts(self.api)
        self.api.quote.set_quote_callback(self.integration)

    def update_snapshot(self, contract: sj.contracts.Contract):
        code = contract.code
        if code not in self.infos.keys():
            self.infos[code] = StatusInfo(**self.api.snapshots([contract]).snapshot[0])

    @staticmethod
    def set_price(price_info: Price, contract: sj.contracts.Contract):
        if price_info.price_type == PriceType.LimitUp:
            price_info.price = contract.limit_up
        elif price_info.price_type == PriceType.LimitDown:
            price_info.price = contract.limit_down
        elif price_info.price_type == PriceType.Unchanged:
            price_info.price = contract.reference
        return PriceGap(**dict(price_info))

    def adjust_condition(
        self, condition: TouchOrderCond, contract: sj.contracts.Contract
    ):
        tconds_dict = condition.touch_cmd.dict()
        tconds_dict.pop("code")
        if tconds_dict:
            for key, value in tconds_dict.items():
                if key not in ["volume", "total_volume"]:
                    tconds_dict[key] = TouchOrder.set_price(Price(**value), contract)
            tconds_dict["order_contract"] = self.contracts[condition.order_cmd.code]
            tconds_dict["order"] = condition.order_cmd.order
            return StoreCond(**tconds_dict)

    def set_condition(self, condition: TouchOrderCond):
        code = condition.touch_cmd.code
        touch_contract = self.contracts[code]
        self.update_snapshot(touch_contract)
        store_condition = self.adjust_condition(condition, touch_contract)
        if store_condition:
            if code in self.conditions.keys():
                self.conditions[code].append(store_condition)
            else:
                self.conditions[code] = [store_condition]
            self.api.quote.subscribe(touch_contract, quote_type="tick")
            self.api.quote.subscribe(touch_contract, quote_type="bidask")

    def delete_condition(self, condition: TouchOrderCond):
        code = condition.touch_cmd.code
        touch_contract = self.contracts[code]
        store_condition = self.adjust_condition(condition, touch_contract)
        if self.conditions.get(code, False) and store_condition:
            if store_condition in self.conditions[code]:
                self.conditions[code].remove(store_condition)
                return self.conditions[code]

    def touch_cond(self, info: typing.Dict, value: typing.Union[StrictInt, float]):
        trend = info.pop("trend")
        if len(info) == 1:
            data = info[list(info.keys())[0]]
            if trend == Trend.Up:
                if data <= value:
                    return True
            elif trend == Trend.Down:
                if data >= value:
                    return True
            elif trend == Trend.Equal:
                if data == value:
                    return True

    def touch(self, code: str):
        conditions = self.conditions.get(code, False)
        if conditions:
            info = self.infos[code].dict()
            for num, conds in enumerate(conditions):
                if not conds.excuted:
                    order = conds.order
                    order_contract = conds.order_contract
                    cond = conds.dict()
                    cond.pop("order")
                    cond.pop("order_contract")
                    cond.pop("excuted")
                    if all(
                        self.touch_cond(value, info[key]) for key, value in cond.items()
                    ):
                        self.conditions[code][num].excuted = True
                        self.api.place_order(order_contract, order)

    def integration(self, topic: str, quote: dict):
        if topic.startswith("MKT/") or topic.startswith("L/"):
            code = topic.split("/")[-1]
            if code in self.infos.keys():
                info = self.infos[code]
                info.close = quote["Close"][0]
                info.high = info.close if info.high < info.close else info.high
                info.low = info.close if info.low > info.close else info.low
                info.total_volume = quote["VolSum"][0]
                info.volume = quote["Volume"][0]
                self.touch(code)
        elif topic.startswith("QUT/") or topic.startswith("Q/"):
            code = topic.split("/")[-1]
            if code in self.infos.keys():
                info = self.infos[code]
                info.buy_price = quote["BidPrice"][0]
                info.sell_price = quote["AskPrice"][0]
                self.touch(code)

    def show_condition(self, code: str = None):
        if not code:
            return self.conditions
        else:
            return self.conditions[code]
