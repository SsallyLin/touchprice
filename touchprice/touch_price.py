import shioaji as sj
import typing
from pydantic import StrictInt
from functools import partial
from touchprice.constant import Trend, PriceType
from touchprice.condition import (
    Price,
    TouchOrderCond,
    OrderCmd,
    TouchCmd,
    StoreCond,
    PriceGap,
    StatusInfo,
    Qty,
    QtyGap,
)


def get_contracts(api: sj.Shioaji):
    contracts = {
        code: contract
        for name, iter_contract in api.Contracts
        for code, contract in iter_contract._code2contract.items()
    }
    return contracts


class TouchOrderExecutor:
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
                    tconds_dict[key] = TouchOrderExecutor.set_price(
                        Price(**value), contract
                    )
            tconds_dict["order_contract"] = self.contracts[condition.order_cmd.code]
            tconds_dict["order"] = condition.order_cmd.order
            return StoreCond(**tconds_dict)

    def add_condition(self, condition: TouchOrderCond):
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
                    cond.pop("result")
                    if all(
                        self.touch_cond(value, info[key]) for key, value in cond.items()
                    ):
                        self.conditions[code][num].excuted = True
                        self.api.place_order(
                            order_contract, order, cb=self.conditions[code][num].result
                        )

    def integration(self, topic: str, quote: dict):
        if "Simtrade" in quote.keys():
            pass
        elif topic.startswith("MKT/") or topic.startswith("L/"):
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
