import shioaji as sj
import typing
import datetime
from shioaji import TickSTKv1, Exchange, BidAskSTKv1
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
    LossProfitCmd,
    StoreLossProfit,
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
        self.conditions: typing.Dict[
            str, typing.List[typing.Union[StoreLossProfit, StoreCond]]
        ] = {}
        self.infos: typing.Dict[str, StatusInfo] = {}
        self.contracts: dict = get_contracts(self.api)
        self.api.quote.set_on_tick_stk_v1_callback(self.integration_tick)
        self.api.quote.set_on_tick_fop_v1_callback(self.integration_tick)
        self.api.quote.set_on_bidask_stk_v1_callback(self.integration_bidask)
        self.api.quote.set_on_bidask_fop_v1_callback(self.integration_bidask)
        self.orders: typing.Dict[str, typing.Dict[str, StoreLossProfit]] = {}

    def update_snapshot(self, contract: sj.contracts.Contract):
        code = contract.target_code if contract.target_code else contract.code
        if code not in self.infos.keys():
            snapshot = self.api.snapshots([contract])[0]
            self.infos[code] = StatusInfo(**snapshot)
            now = datetime.datetime.now(datetime.timezone.utc)
            add_ts = now.timestamp()
            self.infos[code].add_ts = add_ts
            volume = self.infos[code].volume

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
        tconds_dict = condition.touch_cmd.dict(exclude={"code"}, exclude_none=True)
        if tconds_dict:
            for key, value in tconds_dict.items():
                if key not in ["volume", "total_volume", "ask_volume", "bid_volume"]:
                    tconds_dict[key] = TouchOrderExecutor.set_price(
                        Price(**value), contract
                    )
            tconds_dict["order_contract"] = self.contracts[condition.order_cmd.code]
            tconds_dict["order"] = condition.order_cmd.order
            return StoreCond(**tconds_dict)

    def add_condition(self, condition: TouchOrderCond):
        touch_contract = self.contracts[condition.touch_cmd.code]
        self.update_snapshot(touch_contract)
        store_condition = self.adjust_condition(condition, touch_contract)
        if store_condition:
            code = (
                touch_contract.target_code
                if touch_contract.target_code
                else touch_contract.code
            )
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
                    order_contract = conds.order_contract
                    if isinstance(conds, StoreCond):
                        order = conds.order
                        cond = conds.dict(
                            exclude={
                                "order",
                                "order_contract",
                                "excuted",
                                "excuted_cb",
                            },
                            exclude_none=True,
                        )
                        if all(
                            self.touch_cond(value, float(info[key]))
                            for key, value in cond.items()
                        ):
                            self.conditions[code][num].excuted = True
                            self.conditions[code][num].result = self.api.place_order(
                                order_contract,
                                order,
                                cb=self.conditions[code][num].excuted_cb,
                            )

    def integration_bidask(self, exchange: Exchange, bidask: BidAskSTKv1):
        if bidask.simtrade == 1:
            pass
        else:
            code = bidask.code
            if code in self.infos.keys():
                info = self.infos[code]
                if 0 not in bidask.ask_volume:
                    info.buy_price = bidask.bid_price[0]
                    info.sell_price = bidask.ask_price[0]
                    self.touch(code)

    def integration_tick(self, exchange: Exchange, tick: TickSTKv1):
        if tick.simtrade == 1:
            pass
        else:
            code = tick.code
            if code in self.infos.keys():
                info = self.infos[code]
                info.close = tick.close
                info.high = tick.high
                info.low = tick.low
                info.total_volume = tick.total_volume
                info.volume = tick.volume
                if tick.tick_type == 1:
                    info.ask_volume = (
                        info.ask_volume + info.volume
                        if info.ask_volume
                        else info.volume
                    )
                    info.bid_volume = 0
                elif tick.tick_type == 2:
                    info.bid_volume = (
                        info.bid_volume + info.volume
                        if info.bid_volume
                        else info.volume
                    )
                    info.ask_volume = 0
                self.touch(code)

    def show_condition(self, code: str = None):
        if code:
            return self.conditions[code]
        else:
            return self.conditions
