import shioaji as sj
import typing
from pydantic import BaseModel
from functools import partial


class Trend(str, Enum):
    Up = "Up"
    Down = "Down"


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


class PriceInterval(BaseModel):
    price: float = 0.0
    price_type: PriceType = PriceType.LimitPrice
    trend: Trend

    def __init__(
        self,
        trend: Trend,
        price: float = 0.0,
        price_type: PriceType = PriceType.LimitPrice,
    ):
        super().__init__(trend=trend, price=price, price_type=price_type)


class QtyInterval(BaseModel):
    qty: int
    trend: Trend


class Scope(BaseModel):
    scope: typing.Union[int, float]
    scopetype: ScopeType
    price: float = 0.0
    trend: Trend = None

    def __init__(self, scope: typing.Union[int, float], scopetype: ScopeType):
        super().__init__(scope=scope, scopetype=scopetype)


class TouchCond(BaseModel):
    price: PriceInterval = None
    buy_price: PriceInterval = None
    sell_price: PriceInterval = None
    high_price: PriceInterval = None
    low_price: PriceInterval = None
    ups_downs: Scope = None
    scope: Scope = None
    qty: QtyInterval = None
    sum_qty: QtyInterval = None


class TouchCmd(BaseModel):
    code: str
    conditions: TouchCond

    def __init__(self, code: str, conditions: TouchCond):
        super().__init__(**dict(code=code, conditions=conditions))


class OrderCmd(BaseModel):
    code: str
    order: sj.order.Order

    def __init__(self, code: str, order: sj.order.Order):
        super().__init__(**dict(code=code, order=order))


class TouchOrderCond(BaseModel):
    touch_cmd: TouchCmd
    order_cmd: OrderCmd

    def __init__(self, touch_cmd: TouchCmd, order_cmd: OrderCmd):
        super().__init__(**dict(touch_cmd=touch_cmd, order_cmd=order_cmd))


class StoreCond(TouchCmd):
    code: str = None
    order_contract: sj.contracts.Contract
    order: sj.Order
    excuted: bool = False


class StatusInfo(BaseModel):
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
        if code not in self.snapshots.keys():
            self.infos[code] = StatusInfo(
                **self.api.snapshots([contract]).snapshot[0]
            )

    def set_price(
        self, price_info: PriceInterval, contract: sj.contracts.Contract
    ):
        if price_info.price_type == PriceType.LimitUp:
            price_info.price = contract.limit_up
        elif price_info.price_type == PriceType.LimitDown:
            price_info.price = contract.limit_down
        elif price_info.price_type == PriceType.Unchanged:
            price_info.price = contract.reference
        return price_info

    def scope2price(
        self,
        scope_info: Scope,
        info_name: str,
        contract: sj.contracts.Contract
    ):
        if not scope_info:
            scope_info.trend = (
                Trend.Up
                if scope_info.scopetype.endswith("Above")
                else Trend.Down
            )
            ref = contract.reference
            if info_name == "ups_downs":  # 漲跌
                scope_info.price = (
                    ref + scope_info.scope
                    if scope_info.scopetype.startswith("Up")
                    else ref - scope_info.scope
                )
            else:  # 幅度
                temp = (
                    ref * scope_info.scope
                    if scope_info.scopetype.startswith("Up")
                    else -ref * scope_info.scope
                )
                scope_info.price = temp + contract.reference
        return scope_info

    def set_condition(self, condition: TouchOrderCond):
        code = condition.touch_cmd.code
        touch_contract = self.contracts[code]
        self.update_snapshot(touch_contract)
        if condition.touch_cmd.conditions:
            get_price = partial(self.set_price, contract=touch_contract)
            scope2price = partial(self.scope2price, contract=touch_contract)
            store_condition = StoreCond(
                price=get_price(condition.touch_cmd.price),
                buy_price=get_price(condition.touch_cmd.buy_price),
                sell_price=get_price(condition.touch_cmd.sell_price),
                high_price=get_price(condition.touch_cmd.high_price),
                low_price=get_price(condition.touch_cmd.low_price),
                ups_downs=scope2price(
                    condition.touch_cmd.ups_downs, "ups_downs"
                ),
                scope=scope2price(condition.touch_cmd.scope, "scope"),
                qty=condition.touch_cmd.qty, 
                sum_qty=condition.touch_cmd.sum_qty,
                order_contract=self.contracts[condition.order_cmd.code],
                order=condition.order_cmd.order,
            )
        if code in self.conditions.keys():
            self.conditions[code].append(store_condition)
        else:
            self.conditions[code] = [store_condition]
        self.api.quote.subscribe(touch_contract, quote_type="tick")
        self.api.quote.subscribe(touch_contract, quote_type="bidask")
        self.api.quote.set_quote_callback(self.integration)

    def delete_condition(self, condition: TouchOrderCond):
        code = condition.touch_cmd.code
        if condition.touch_cmd.conditions:
            store_condition = StoreCond(
                price=condition.touch_cmd.price,
                buy_price=condition.touch_cmd.buy_price,
                sell_price=condition.touch_cmd.sell_price,
                high_price=condition.touch_cmd.high_price,
                low_price=condition.touch_cmd.low_price,
                ups_downs=condition.touch_cmd.ups_downs,
                scope=condition.touch_cmd.scope,
                qty=condition.touch_cmd.qty,
                sum_qty=condition.touch_cmd.sum_qty,
                order_contract=self.contracts[condition.order_cmd.code],
                order=condition.order_cmd.order,
            )
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
