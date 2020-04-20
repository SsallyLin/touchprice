import shioaji as sj
import typing
from .core import Base, DisplayCore, MetaContent, Dataset, UpdateContent
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


class ScopeType(str, Enum):
    UpAbove = "UpAbove"  # 漲幅超過
    DownAbove = "DownAbove"  # 跌幅超過
    UpBelow = "UpBelow"  # 漲幅低於
    DownBelow = "DownBelow"  # 跌幅低於


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


class Scope(PriceGap):
    scope: typing.Union[StrictInt, float]
    scope_type: ScopeType
    price: float = 0.0
    trend: Trend = None

    def __init__(self, scope: typing.Union[StrictInt, float], scope_type: ScopeType):
        super().__init__(**dict(scope=scope, scope_type=scope_type))


class QtyGap(Base):
    qty: int
    trend: Trend

class Qty(QtyGap):
    def __init__(self, qty: int, trend: Trend):
        super().__init__(**dict(qty=qty, trend=trend))


class TouchCond(Base):
    price: Price = None
    buy_price: Price = None
    sell_price: Price = None
    high_price: Price = None
    low_price: Price = None
    ups_downs: Scope = None
    scope: Scope = None
    qty: Qty = None
    sum_qty: Qty = None

    def __init__(
        self,
        price: Price = None,
        buy_price: Price = None,
        sell_price: Price = None,
        high_price: Price = None,
        low_price: Price = None,
        ups_downs: Price = None,
        scope: Price = None,
        qty: Qty = None,
        sum_qty: Qty = None,
    ):
        super().__init__(
            **dict(
                price=price,
                buy_price=buy_price,
                sell_price=sell_price,
                high_price=high_price,
                low_price=low_price,
                ups_downs=ups_downs,
                scope=scope,
                qty=qty,
                sum_qty=sum_qty,
            )
        )


class TouchCmd(Base):
    code: str
    conditions: TouchCond

    def __init__(self, code: str, conditions: TouchCond):
        super().__init__(**dict(code=code, conditions=conditions))


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
    price: PriceGap = None
    buy_price: PriceGap = None
    sell_price: PriceGap = None
    high_price: PriceGap = None
    low_price: PriceGap = None
    ups_downs: PriceGap = None
    scope: PriceGap = None
    qty: QtyGap = None
    sum_qty: QtyGap = None
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
        for code, contract in iter_contract._code1contract.items()
    }
    return contracts


class TouchOrder:
    def __init__(self, api: sj.Shioaji):
        self.api: sj.Shioaji = api
        self.conditions: typing.Dict[str, typing.List[StoreCond]] = {}
        self.infos: typing.Dict[str, StatusInfo] = {}
        self.contracts: dict = get_contracts(self.api)

    def update_snapshot(self, contract: sj.contracts.Contract):
        code = contract.code
        if code not in self.infos.keys():
            self.infos[code] = StatusInfo(**self.api.snapshots([contract]).snapshot[0])

    def set_price(self, price_info: Price, contract: sj.contracts.Contract):
        if price_info.price_type == PriceType.LimitUp:
            price_info.price = contract.limit_up
        elif price_info.price_type == PriceType.LimitDown:
            price_info.price = contract.limit_down
        elif price_info.price_type == PriceType.Unchanged:
            price_info.price = contract.reference
        return price_info

    def scope2price(
        self, scope_info: Scope, info_name: str, contract: sj.contracts.Contract
    ):
        trend = Trend.Up if scope_info.scope_type.endswith("Above") else Trend.Down
        ref = contract.reference
        if info_name == "ups_downs":  # 漲跌
            price = (
                ref + scope_info.scope
                if scope_info.scope_type.startswith("Up")
                else ref - scope_info.scope
            )
        else:  # 幅度
            temp = (
                ref * scope_info.scope
                if scope_info.scope_type.startswith("Up")
                else -ref * scope_info.scope
            )
            price = temp + contract.reference
        price = PriceGap(price=price, trend=trend)
        return price

    def adjust_codition(
        self, conditions: TouchOrderCond, contract: sj.contracts.Contract
    ):
        get_price = partial(self.set_price, contract=contract)
        scope2price = partial(self.scope2price, contract=contract)
        tconds_dict = conditions.touch_cmd.conditions.dict()
        use_get_price = ["price", "buy_price", "sell_price", "high_price", "low_price"]
        use_scope2 = ["ups_downs", "scope"]
        temp_dict = {}
        for key, value in tconds_dict.items():
            if key in use_get_price:
                temp_dict[key] = get_price(value)
            elif key in use_scope2:
                temp_dict[key] = scope2price(value, key)
            else:
                temp_dict[key] = value
        temp_dict["order_contract"] = self.contracts[conditions.order_cmd.code]
        temp_dict["order"] = (conditions.order_cmd.order)
        return StoreCond(**temp_dict)

    def set_condition(self, condition: TouchOrderCond):
        code = condition.touch_cmd.code
        touch_contract = self.contracts[code]
        self.update_snapshot(touch_contract)
        touch_condition = condition.touch_cmd.conditions
        if touch_condition:
            store_condition = self.adjust_codition(touch_condition, touch_contract)
        if code in self.conditions.keys():
            self.conditions[code].append(store_condition)
        else:
            self.conditions[code] = [store_condition]
        self.api.quote.subscribe(touch_contract, quote_type="tick")
        self.api.quote.subscribe(touch_contract, quote_type="bidask")
        self.api.quote.set_quote_callback(self.integration)

    def delete_condition(self, condition: TouchOrderCond):
        code = condition.touch_cmd.code
        touch_contract = self.contracts[code]
        if condition.touch_cmd.conditions:
            store_condition = self.adjust_codition(condition, touch_contract)
        if self.conditions.get(code, False):
            if store_condition in self.conditions[code]:
                self.conditions[code].remove(store_condition)
                return self.conditions[code]

    def touch(self, code: str):
        pass

    def integration(self, topic, quote):
        if topic.startswith("MKT/"):
            code = topic.split("/")[-1]
            if code in self.infos.keys():
                info = self.infos[code]
                info.close = quote["Close"]
                info.high = info.close if info.high < info.close else info.high
                info.low = info.close if info.low > info.close else info.low
                info.total_volume = quote["VolSum"]
                info.volume = quote["Volume"]
                self.touch(code)
        elif topic.startswith("QUT/"):
            code = topic.split("/")[-1]
            if code in self.infos.keys():
                info = self.infos[code]
                info.buy_price = quote["BidPrice"][0]
                info.sell_price = quote["AskPrice"][0]
                self.touch(code)
